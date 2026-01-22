from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session

from . import models, schemas
from .auth import authenticate_user, get_current_user, get_current_user_optional, get_password_hash
from .database import Base, engine, get_db
from .executor import run_script

Base.metadata.create_all(bind=engine)

app = FastAPI(title="运维工具箱")

# 配置 Session 中间件
app.add_middleware(
    SessionMiddleware,
    secret_key="your-secret-key-here-change-in-production",  # 在生产环境中应该从环境变量读取
    max_age=86400,  # 24小时
    same_site="lax",
    https_only=False,  # 开发环境设为 False，生产环境应设为 True
)

templates = Jinja2Templates(directory="templates")
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """登录页面"""
    error = request.query_params.get("error", "")
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": error,
        },
    )


@app.post("/api/login")
def login(
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
    request: Request = ...,
    db: Session = Depends(get_db),
):
    """登录接口"""
    user = authenticate_user(db, username, password)
    if not user:
        return RedirectResponse(
            url="/login?error=用户名或密码错误", status_code=status.HTTP_303_SEE_OTHER
        )
    
    # 设置 Session
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    
    # 重定向到原始页面或首页
    return RedirectResponse(url=next, status_code=status.HTTP_303_SEE_OTHER)


@app.post("/api/logout")
def logout(request: Request):
    """登出接口"""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/api/me", response_model=schemas.UserOut)
def get_current_user_info(current_user: models.User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return current_user


@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_current_user_optional),
):
    # 如果未登录，重定向到登录页面
    if not current_user:
        next_url = str(request.url)
        return RedirectResponse(url=f"/login?next={next_url}", status_code=status.HTTP_303_SEE_OTHER)
    
    categories = db.query(models.ScriptCategory).order_by(
        models.ScriptCategory.order
    )
    scripts = (
        db.query(models.ScriptItem)
        .filter(models.ScriptItem.enabled.is_(True))
        .order_by(models.ScriptItem.update_time.desc())
        .limit(20)
        .all()
    )
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "categories": categories,
            "recent_scripts": scripts,
            "current_user": current_user,
        },
    )


@app.get("/manage/scripts", response_class=HTMLResponse)
def manage_scripts(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_current_user_optional),
):
    # 如果未登录，重定向到登录页面
    if not current_user:
        next_url = str(request.url)
        return RedirectResponse(url=f"/login?next={next_url}", status_code=status.HTTP_303_SEE_OTHER)
    
    categories = (
        db.query(models.ScriptCategory)
        .order_by(models.ScriptCategory.order)
        .all()
    )
    return templates.TemplateResponse(
        "manage_scripts.html",
        {
            "request": request,
            "categories": categories,
            "current_user": current_user,
        },
    )


@app.get(
    "/scripts/{script_id}", response_class=HTMLResponse, name="script_detail"
)
def script_detail(
    script_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_current_user_optional),
):
    # 如果未登录，重定向到登录页面
    if not current_user:
        next_url = str(request.url)
        return RedirectResponse(url=f"/login?next={next_url}", status_code=status.HTTP_303_SEE_OTHER)
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
            "current_user": current_user,
        },
    )


@app.get("/api/categories", response_model=List[schemas.ScriptCategoryOut])
def list_categories(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    items = db.query(models.ScriptCategory).order_by(
        models.ScriptCategory.order
    )
    return items.all()


@app.post("/api/categories", response_model=schemas.ScriptCategoryOut)
def create_category(
    payload: schemas.ScriptCategoryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
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
    current_user: models.User = Depends(get_current_user),
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
    current_user: models.User = Depends(get_current_user),
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
    current_user: models.User = Depends(get_current_user),
):
    query = db.query(models.ScriptItem)
    if category_id is not None:
        query = query.filter(models.ScriptItem.category_id == category_id)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(models.ScriptItem.title.like(like))
    return query.order_by(models.ScriptItem.update_time.desc()).all()


@app.get("/api/scripts/{script_id}", response_model=schemas.ScriptItemOut)
def get_script(
    script_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    script = db.query(models.ScriptItem).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="脚本不存在")
    return script


@app.post("/api/scripts", response_model=schemas.ScriptItemOut)
def create_script(
    payload: schemas.ScriptItemCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    script = models.ScriptItem(
        category_id=payload.category_id,
        title=payload.title,
        description=payload.description,
        script_type=payload.script_type,
        exec_command_template=payload.exec_command_template,
        script_path=payload.script_path,
        enabled=payload.enabled,
        is_dangerous=payload.is_dangerous,
    )
    db.add(script)
    db.commit()
    db.refresh(script)

    if payload.initial_content is not None:
        scripts_dir = Path("scripts")
        scripts_dir.mkdir(exist_ok=True)
        script_path = (
            Path(script.script_path)
            if Path(script.script_path).is_absolute()
            else scripts_dir / script.script_path
        )
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(payload.initial_content, encoding="utf-8")

        version = models.ScriptVersion(
            script_id=script.id,
            version=1,
            content=payload.initial_content,
            editor="system",
        )
        db.add(version)
        db.commit()

    return script


@app.put("/api/scripts/{script_id}")
def update_script(
    script_id: int,
    payload: schemas.ScriptItemUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
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
    current_user: models.User = Depends(get_current_user),
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
def get_script_content(
    script_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
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
    current_user: models.User = Depends(get_current_user),
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
    current_user: models.User = Depends(get_current_user),
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
def get_exec(
    exec_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    rec = db.query(models.ScriptExecRecord).get(exec_id)
    if not rec:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    return rec


@app.get("/api/exec/{exec_id}/log", response_class=PlainTextResponse)
def get_exec_log(
    exec_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    rec = db.query(models.ScriptExecRecord).get(exec_id)
    if not rec:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    if not rec.log_path:
        return ""
    path = Path(rec.log_path)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

