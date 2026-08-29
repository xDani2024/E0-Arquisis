from fastapi import FastAPI


app = FastAPI(title="EnergyShark API")


@app.get("/health")
def health():
    return {"status": "healthy"}