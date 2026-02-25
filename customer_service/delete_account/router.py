from fastapi import APIRouter, Depends
from shared.internal_auth import require_user_id

router = APIRouter(
	prefix="/users/{user_id}",
	tags=["user-account"],
	dependencies=[Depends(require_user_id)],
)

# TODO: Реализовать эндпоинты для удаления аккаунта
