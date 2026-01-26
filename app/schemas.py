from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class UserBase(BaseModel):
    username: str
    email: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserOut(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    create_time: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class ScriptCategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    order: int = 0


class ScriptCategoryCreate(ScriptCategoryBase):
    pass


class ScriptCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None


class ScriptCategoryOut(ScriptCategoryBase):
    id: int

    class Config:
        from_attributes = True


class ScriptItemBase(BaseModel):
    category_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    script_type: str
    exec_command_template: Optional[str] = None
    script_path: str
    enabled: bool = True
    is_dangerous: bool = False


class ScriptItemCreate(ScriptItemBase):
    initial_content: Optional[str] = None


class ScriptItemUpdate(BaseModel):
    category_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    script_type: Optional[str] = None
    exec_command_template: Optional[str] = None
    script_path: Optional[str] = None
    enabled: Optional[bool] = None
    is_dangerous: Optional[bool] = None


class ScriptItemOut(ScriptItemBase):
    id: int
    create_time: datetime
    update_time: datetime
    category_name: Optional[str] = None

    class Config:
        from_attributes = True


class ScriptContentOut(BaseModel):
    content: str
    version: int


class ScriptContentUpdate(BaseModel):
    content: str
    editor: Optional[str] = None
    remark: Optional[str] = None


class ScriptExecStart(BaseModel):
    params_json: Optional[str] = None
    operator: Optional[str] = None


class ScriptExecOut(BaseModel):
    id: int
    script_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str
    exit_code: Optional[int] = None
    operator: Optional[str] = None

    class Config:
        from_attributes = True

