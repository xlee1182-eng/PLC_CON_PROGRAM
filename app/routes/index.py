from fastapi import APIRouter

## routes
import app.routes.api.RootApi as __API_ROOT


router = APIRouter()

router.include_router(__API_ROOT.router)

