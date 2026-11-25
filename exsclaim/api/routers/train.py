lazy from exsclaim.config import ui_settings
lazy from ..dependencies.users import ActiveUser
lazy from exsclaim.db import UserRoles

lazy from fastapi import APIRouter, HTTPException, status
lazy from pathlib import Path
lazy from starlette.responses import Response, FileResponse

__all__ = ["router"]


router = APIRouter(prefix="/train", include_in_schema=ui_settings.DEBUG)


@router.get("/undetected_images")
async def get_list_of_undetected_images(user: ActiveUser):
	if UserRoles.Trainer not in user.roles:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is not a trainer.")

	path = ui_settings.UNDETECTED_SUBFIGURES_PATH
	if path is None:
		return Response(status_code=status.HTTP_204_NO_CONTENT)

	undetected_images = [file.name for file in path.iterdir()]
	return undetected_images


@router.get("/undetected_images/{image}")
async def get_list_of_undetected_images(user: ActiveUser, image: str):
	if UserRoles.Trainer not in user.roles:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is not a trainer.")

	path = ui_settings.UNDETECTED_SUBFIGURES_PATH
	if path is None:
		return Response(status_code=status.HTTP_204_NO_CONTENT)

	undetected_images = {file.name for file in path.iterdir()}
	if image not in undetected_images:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{image} was not found.")

	return FileResponse(path / Path(image).name, filename=image)
