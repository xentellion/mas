from fastapi import APIRouter
from api.api_models import Data
from api.backend.rpc_client import RpcClient


router = APIRouter()


@router.get("/")
def test():
    return {"response": "server_online"}


@router.post("/")
def send(data: Data):
    client = RpcClient()
    response = client.call(data)
    return {"response": response}
