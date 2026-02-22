from fastapi import APIRouter

router = APIRouter(
	prefix="/users/{user_id}",
	tags=["user-account"],
)

# TODO: Реализовать эндпоинты для удаления аккаунта
