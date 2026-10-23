from fastapi import FastAPI

app = FastAPI()

@app.get("/handshake")
def handshake():
    return {"status": "ok"}
