from fastapi import FastAPI


# Create our FastAPI application.
app = FastAPI()


# Define an HTTP GET endpoint.
# When someone visits "/", FastAPI will run this function.
@app.get("/")
def root():
    return {"message": "Incident Tracker API is running"}


# Another endpoint that we can use to test our API.
@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }