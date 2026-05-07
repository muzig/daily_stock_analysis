from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from bot.handler import handle_telegram_webhook

router = APIRouter()


@router.post("/telegram")
async def telegram_webhook(request: Request):
    """
    处理 Telegram Webhook 请求

    Telegram 会将消息通过 POST 请求发送到这个端点。
    """
    try:
        body = await request.body()
        headers = dict(request.headers)

        response = handle_telegram_webhook(headers, body)

        return JSONResponse(
            content=response.data,
            status_code=response.status_code
        )
    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )
