from fastapi import FastAPI
from .models import ResonanceFrame

app = FastAPI(title="AAL Hub API")

# In v0 this will be simple; later we'll integrate with Hub/Bus.


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/frame")
def send_frame(frame: ResonanceFrame):
    # TODO: publish to a chosen topic (e.g. oracle.request)
    # This will be wired once Hub and API share a Bus instance.
    return {"received": frame.id}
