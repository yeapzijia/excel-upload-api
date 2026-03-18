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

# Root health check
@app.get("/")
async def health_check():
    return {"status": "ok"}

# Swagger 2.0 descriptor for K2 compatibility
@app.get("/swagger.json")
async def swagger_json():
    return {
        "swagger": "2.0",
        "info": {
            "title": "Test Excel API",
            "description": "A test API for K2",
            "version": "1.0.0"
        },
        "host": "affectionate-light-production.up.railway.app",
        "basePath": "/",
        "schemes": ["https"],
        "consumes": ["application/json"],
        "produces": ["application/json"],
        "paths": {
            "/todos/{id}": {
                "get": {
                    "operationId": "getTodoById",
                    "summary": "Get a single todo item",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "type": "integer",
                            "format": "int32"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "OK",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "userId":    {"type": "integer"},
                                    "id":        {"type": "integer"},
                                    "title":     {"type": "string"},
                                    "completed": {"type": "boolean"}
                                }
                            }
                        }
                    }
                }
            },
            "/excel/upload": {
                "post": {
                    "operationId": "uploadExcel",
                    "summary": "Upload an Excel file",
                    "consumes": ["multipart/form-data"],
                    "parameters": [
                        {
                            "name": "file",
                            "in": "formData",
                            "required": True,
                            "type": "file"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "OK",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "status":        {"type": "string"},
                                    "message":       {"type": "string"},
                                    "fileName":      {"type": "string"},
                                    "fileSize":      {"type": "integer"},
                                    "uploadedAt":    {"type": "string"},
                                    "sheetName":     {"type": "string"},
                                    "rowsProcessed": {"type": "integer"},
                                    "errorDetails":  {"type": "string"},
                                    "downloadUrl":   {"type": "string"}
                                }
                            }
                        }
                    }
                }
            },
            "/excel/download/{temp_filename}": {
                "get": {
                    "operationId": "downloadExcel",
                    "summary": "Download uploaded Excel file",
                    "parameters": [
                        {
                            "name": "temp_filename",
                            "in": "path",
                            "required": True,
                            "type": "string"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "OK"
                        }
                    }
                }
            }
        }
    }

# Log incoming requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f">>> {request.method} {request.url}")
    print(f">>> Headers: {dict(request.headers)}")
    response = await call_next(request)
    print(f">>> Response status: {response.status_code}")
    return response

# Todo endpoint
@app.get("/todos/{id}")
async def get_todo(id: int):
    response = {
        "userId": 1,
        "id": id,
        "title": "Sample Todo",
        "completed": False
    }
    # ✅ Log full response
    print(f">>> TODO RESPONSE:")
    print(f">>> userId:    {response['userId']}")
    print(f">>> id:        {response['id']}")
    print(f">>> title:     {response['title']}")
    print(f">>> completed: {response['completed']}")
    return response

# Excel upload endpoint
@app.post("/excel/upload")
async def upload_excel(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xlsx', '.xls')):
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "Only .xlsx or .xls files are allowed"
            }
        )
    contents = await file.read()
    df = pd.read_excel(io.BytesIO(contents))
    excel_file = pd.ExcelFile(io.BytesIO(contents))
    sheet_name = excel_file.sheet_names[0]
    data = df.to_dict(orient="records")
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    temp_file.write(contents)
    temp_file.close()

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
        "downloadUrl": f"https://affectionate-light-production.up.railway.app/excel/download/{os.path.basename(temp_file.name)}"
    }

    # ✅ Log full response
    print(f">>> UPLOAD RESPONSE:")
    print(f">>> status:        {response['status']}")
    print(f">>> message:       {response['message']}")
    print(f">>> fileName:      {response['fileName']}")
    print(f">>> fileSize:      {response['fileSize']}")
    print(f">>> uploadedAt:    {response['uploadedAt']}")
    print(f">>> sheetName:     {response['sheetName']}")
    print(f">>> rowsProcessed: {response['rowsProcessed']}")
    print(f">>> errorDetails:  {response['errorDetails']}")
    print(f">>> downloadUrl:   {response['downloadUrl']}")

    return response

# Excel download endpoint
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
