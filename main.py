from fastapi import FastAPI, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from datetime import datetime
import pandas as pd
import io
import tempfile
import os

app = FastAPI()

# Allow K2 Designer or any origin to call
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ NEW: Root health check (fixes K2 first probe returning 0)
@app.get("/")
async def health_check():
    return {"status": "ok"}

# ✅ NEW: Log incoming headers for debugging (remove after fixing 403)
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f">>> {request.method} {request.url}")
    print(f">>> Headers: {dict(request.headers)}")
    response = await call_next(request)
    print(f">>> Response status: {response.status_code}")
    return response

@app.get("/todos/{id}")
async def get_todo(id: int):
    return {
        "userId": 1,
        "id": id,
        "title": "Sample Todo",
        "completed": False
    }

@app.post("/excel/upload")
async def upload_excel(file: UploadFile = File(...)):
    # Check file type
    if not file.filename.endswith(('.xlsx', '.xls')):
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "Only .xlsx or .xls files are allowed"
            }
        )

    # Read file content
    contents = await file.read()

    # Parse Excel into DataFrame
    df = pd.read_excel(io.BytesIO(contents))
    excel_file = pd.ExcelFile(io.BytesIO(contents))
    sheet_name = excel_file.sheet_names[0]
    data = df.to_dict(orient="records")

    # Save the uploaded file temporarily for download
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    temp_file.write(contents)
    temp_file.close()

    # Prepare JSON metadata + file download URL
    response = {
        "status": "success",
        "message": "File uploaded successfully",
        "fileName": file.filename,
        "fileSize": len(contents),
        "uploadedAt": datetime.now().isoformat(),
        "sheetName": sheet_name,
        "rowsProcessed": len(df),
        "errorDetails": "",
        "data": data,
        "downloadUrl": f"/excel/download/{os.path.basename(temp_file.name)}"
    }

    return response

# Endpoint to download exact original file
@app.get("/excel/download/{temp_filename}")
async def download_excel(temp_filename: str):
    temp_path = os.path.join(tempfile.gettempdir(), temp_filename)
    if not os.path.exists(temp_path):
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "File not found"}
        )
    return FileResponse(
        path=temp_path,
        filename=temp_filename,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
