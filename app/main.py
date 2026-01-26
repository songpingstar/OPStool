from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from . import auth, models, schemas
from .database import Base, engine, get_db
from .executor import run_script

Base.metadata.create_all(bind=engine)

app = FastAPI(title="运维工具箱")

templates = Jinja2Templates(directory="templates")
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


async def get_current_user_from_cookie(
    request: Request, db: Session = Depends(get_db)
) -> Optional[models.User]:
    token = request.cookies.get("access_token")
    if not token:
        return None
    return auth.get_current_user(token, db)


async def require_auth(
    request: Request, db: Session = Depends(get_db)
) -> models.User:
    user = await get_current_user_from_cookie(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )
    return user


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/api/login")
def login(
    request: Request,
    payload: schemas.LoginRequest,
    db: Session = Depends(get_db),
):
    user = auth.authenticate_user(db, payload.username, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    access_token = auth.create_access_token(data={"sub": user.username})
    
    user.last_login = datetime.utcnow()
    db.commit()
    
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return response


@app.post("/api/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("access_token")
    return response


@app.get("/api/me", response_model=schemas.UserOut)
async def get_me(current_user: models.User = Depends(require_auth)):
    return current_user


@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request, db: Session = Depends(get_db)
):
    current_user = await get_current_user_from_cookie(request, db)
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    categories = db.query(models.ScriptCategory).order_by(
        models.ScriptCategory.order
    )
    
    from sqlalchemy import func, desc
    subquery = (
        db.query(
            models.ScriptExecRecord.script_id,
            func.max(models.ScriptExecRecord.start_time).label('last_exec_time')
        )
        .group_by(models.ScriptExecRecord.script_id)
        .subquery()
    )
    
    scripts = (
        db.query(models.ScriptItem)
        .join(subquery, models.ScriptItem.id == subquery.c.script_id)
        .order_by(desc(subquery.c.last_exec_time))
        .limit(20)
        .all()
    )
    
    for script in scripts:
        last_exec = db.query(models.ScriptExecRecord).filter(
            models.ScriptExecRecord.script_id == script.id
        ).order_by(models.ScriptExecRecord.start_time.desc()).first()
        script.last_exec_time = last_exec.start_time if last_exec else None
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "categories": categories,
            "recent_scripts": scripts,
            "current_user": current_user,
        },
    )


@app.get("/manage/categories", response_class=HTMLResponse)
async def manage_categories(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_auth),
):
    return templates.TemplateResponse(
        "manage_categories.html",
        {
            "request": request,
        },
    )


@app.get("/manage/scripts", response_class=HTMLResponse)
async def manage_scripts(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_auth),
):
    return templates.TemplateResponse(
        "manage_scripts.html",
        {
            "request": request,
        },
    )


@app.get(
    "/scripts/{script_id}", response_class=HTMLResponse, name="script_detail"
)
async def script_detail(
    script_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_auth),
):
    script = db.query(models.ScriptItem).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="脚本不存在")
    latest_version = (
        db.query(models.ScriptVersion)
        .filter(models.ScriptVersion.script_id == script_id)
        .order_by(models.ScriptVersion.version.desc())
        .first()
    )
    recent_exec = (
        db.query(models.ScriptExecRecord)
        .filter(models.ScriptExecRecord.script_id == script_id)
        .order_by(models.ScriptExecRecord.start_time.desc())
        .limit(10)
        .all()
    )
    return templates.TemplateResponse(
        "script_detail.html",
        {
            "request": request,
            "script": script,
            "latest_version": latest_version,
            "recent_exec": recent_exec,
        },
    )


@app.get("/api/categories", response_model=List[schemas.ScriptCategoryOut])
def list_categories(db: Session = Depends(get_db)):
    items = db.query(models.ScriptCategory).order_by(
        models.ScriptCategory.order
    )
    return items.all()


@app.post("/api/categories", response_model=schemas.ScriptCategoryOut)
def create_category(
    payload: schemas.ScriptCategoryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_auth),
):
    obj = models.ScriptCategory(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@app.put("/api/categories/{category_id}")
def update_category(
    category_id: int,
    payload: schemas.ScriptCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_auth),
):
    obj = db.query(models.ScriptCategory).get(category_id)
    if not obj:
        raise HTTPException(status_code=404, detail="分类不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    return {"ok": True}


@app.delete("/api/categories/{category_id}")
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_auth),
):
    obj = db.query(models.ScriptCategory).get(category_id)
    if not obj:
        raise HTTPException(status_code=404, detail="分类不存在")
    db.delete(obj)
    db.commit()
    return {"ok": True}


@app.get("/api/scripts", response_model=List[schemas.ScriptItemOut])
def list_scripts(
    category_id: Optional[int] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.ScriptItem)
    if category_id is not None:
        query = query.filter(models.ScriptItem.category_id == category_id)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(models.ScriptItem.title.like(like))
    scripts = query.order_by(models.ScriptItem.update_time.desc()).all()
    
    result = []
    for script in scripts:
        category_name = None
        if script.category:
            category_name = script.category.name
        script_dict = {
            "id": script.id,
            "category_id": script.category_id,
            "title": script.title,
            "description": script.description,
            "script_type": script.script_type,
            "exec_command_template": script.exec_command_template,
            "script_path": script.script_path,
            "enabled": script.enabled,
            "is_dangerous": script.is_dangerous,
            "create_time": script.create_time,
            "update_time": script.update_time,
            "category_name": category_name
        }
        result.append(script_dict)
    return result


@app.get("/api/scripts/{script_id}", response_model=schemas.ScriptItemOut)
def get_script(script_id: int, db: Session = Depends(get_db)):
    script = db.query(models.ScriptItem).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="脚本不存在")
    return script


@app.post("/api/scripts", response_model=schemas.ScriptItemOut)
def create_script(
    payload: schemas.ScriptItemCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_auth),
):
    script = models.ScriptItem(
        category_id=payload.category_id,
        title=payload.title,
        description=payload.description,
        script_type=payload.script_type,
        exec_command_template=payload.exec_command_template,
        script_path=None,
        enabled=payload.enabled,
        is_dangerous=payload.is_dangerous,
    )
    db.add(script)
    db.commit()
    db.refresh(script)

    scripts_dir = Path("scripts")
    scripts_dir.mkdir(exist_ok=True)
    
    ext_map = {
        "python": ".py",
        "powershell": ".ps1",
        "shell": ".sh"
    }
    ext = ext_map.get(payload.script_type, ".py")
    script_path = scripts_dir / f"{script.id}{ext}"
    
    if payload.initial_content is not None:
        script_path.write_text(payload.initial_content, encoding="utf-8")

        version = models.ScriptVersion(
            script_id=script.id,
            version=1,
            content=payload.initial_content,
            editor="system",
        )
        db.add(version)
        db.commit()
    
    script.script_path = str(script_path)
    db.commit()
    db.refresh(script)

    return script


@app.put("/api/scripts/{script_id}")
def update_script(
    script_id: int,
    payload: schemas.ScriptItemUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_auth),
):
    script = db.query(models.ScriptItem).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="脚本不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(script, k, v)
    db.commit()
    return {"ok": True}


@app.delete("/api/scripts/{script_id}")
def delete_script(
    script_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_auth),
):
    script = db.query(models.ScriptItem).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="脚本不存在")
    
    # 删除脚本文件
    scripts_dir = Path("scripts")
    script_path = (
        Path(script.script_path)
        if Path(script.script_path).is_absolute()
        else scripts_dir / script.script_path
    )
    if script_path.exists():
        try:
            script_path.unlink()
        except Exception as e:
            # 如果文件删除失败，记录日志但不阻止删除操作
            print(f"警告：删除脚本文件失败 {script_path}: {e}")
    
    # 删除关联的版本记录
    db.query(models.ScriptVersion).filter(
        models.ScriptVersion.script_id == script_id
    ).delete()
    
    # 删除关联的执行记录（可选：也可以保留历史记录，这里选择删除）
    db.query(models.ScriptExecRecord).filter(
        models.ScriptExecRecord.script_id == script_id
    ).delete()
    
    # 删除脚本条目本身
    db.delete(script)
    db.commit()
    return {"ok": True}


@app.get("/api/scripts/{script_id}/content", response_model=schemas.ScriptContentOut)
def get_script_content(script_id: int, db: Session = Depends(get_db)):
    script = db.query(models.ScriptItem).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="脚本不存在")
    latest_version = (
        db.query(models.ScriptVersion)
        .filter(models.ScriptVersion.script_id == script_id)
        .order_by(models.ScriptVersion.version.desc())
        .first()
    )
    if latest_version:
        return schemas.ScriptContentOut(
            content=latest_version.content, version=latest_version.version
        )

    scripts_dir = Path("scripts")
    script_path = (
        Path(script.script_path)
        if Path(script.script_path).is_absolute()
        else scripts_dir / script.script_path
    )
    if script_path.exists():
        content = script_path.read_text(encoding="utf-8")
    else:
        content = ""
    return schemas.ScriptContentOut(content=content, version=0)


@app.put("/api/scripts/{script_id}/content")
def update_script_content(
    script_id: int,
    payload: schemas.ScriptContentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_auth),
):
    script = db.query(models.ScriptItem).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="脚本不存在")

    latest_version = (
        db.query(models.ScriptVersion)
        .filter(models.ScriptVersion.script_id == script_id)
        .order_by(models.ScriptVersion.version.desc())
        .first()
    )
    next_ver = 1 if not latest_version else latest_version.version + 1

    scripts_dir = Path("scripts")
    script_path = (
        Path(script.script_path)
        if Path(script.script_path).is_absolute()
        else scripts_dir / script.script_path
    )
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(payload.content, encoding="utf-8")

    version = models.ScriptVersion(
        script_id=script.id,
        version=next_ver,
        content=payload.content,
        editor=payload.editor or "unknown",
        remark=payload.remark,
    )
    db.add(version)
    db.commit()
    return {"ok": True, "version": next_ver}


@app.post("/api/scripts/{script_id}/run", response_model=schemas.ScriptExecOut)
def run_script_api(
    script_id: int,
    payload: schemas.ScriptExecStart,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_auth),
):
    script = db.query(models.ScriptItem).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="脚本不存在")
    exec_record = run_script(
        db=db,
        script=script,
        params_json=payload.params_json,
        operator=payload.operator,
    )
    return exec_record


@app.get("/api/exec/{exec_id}", response_model=schemas.ScriptExecOut)
def get_exec(exec_id: int, db: Session = Depends(get_db)):
    rec = db.query(models.ScriptExecRecord).get(exec_id)
    if not rec:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    return rec


@app.get("/api/exec/{exec_id}/log", response_class=PlainTextResponse)
def get_exec_log(exec_id: int, db: Session = Depends(get_db)):
    rec = db.query(models.ScriptExecRecord).get(exec_id)
    if not rec:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    if not rec.log_path:
        return ""
    path = Path(rec.log_path)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

