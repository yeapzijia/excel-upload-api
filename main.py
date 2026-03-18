from fastapi import FastAPI, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from datetime import datetime
import pandas as pd
import io
import tempfile
import os

app = FastAPI()

# Allow all origins (for K2 Designer)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/")
async def health_check():
    return {"status": "ok"}

# ✅ K2-compatible Swagger 2.0
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

        # ✅ IMPORTANT: definitions (K2 needs this)
        "definitions": {
            "Todo": {
                "type": "object",
                "properties": {
                    "userId": {"type": "integer"},
                    "id": {"type": "integer"},
                    "title": {"type": "string"},
                    "completed": {"type": "boolean"}
                }
            },
            "UploadResponse": {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "message": {"type": "string"},
                    "fileName": {"type": "string"},
                    "fileSize": {"type": "integer"},
                    "uploadedAt": {"type": "string"},
                    "sheetName": {"type": "string"},
                    "rowsProcessed": {"type": "integer"},
                    "errorDetails": {"type": "string"},
                    "downloadUrl": {"type": "string"}
                }
            }
        },

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
                                "$ref": "#/definitions/Todo"
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
                                "$ref": "#/definitions/UploadResponse"
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
                            "description": "File download (no JSON response)"
                        }
                    }
                }
            }
        }
    }

# Debug middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f">>> {request.method} {request.url}")
    response = await call_next(request)
    print(f">>> Response status: {response.status_code}")
    return response

# GET Todo
@app.get("/todos/{id}")
async def get_todo(id: int):
    return {
        "userId": 1,
        "id": id,
        "title": "Sample Todo",
        "completed": False
    }

# Upload Excel
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

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    temp_file.write(contents)
    temp_file.close()

    return {
        "status": "success",
        "message": "File uploaded successfully",
        "fileName": file.filename,
        "fileSize": len(contents),
        "uploadedAt": datetime.now().isoformat(),
        "sheetName": sheet_name,
        "rowsProcessed": len(df),
        "errorDetails": "",
        "downloadUrl": f"/excel/download/{os.path.basename(temp_file.name)}"
    }

# Download Excel
@app.get("/excel/download/{temp_filename}")
async def download_excel(temp_filename: str):
    temp_path = os.path.join(tempfile.gettempdir(), temp_filename)

    if not os.path.exists(temp_path):
        return JSONResponse(
            status_code=404,
            content={
                "status": "error",
                "message": "File not found"
            }
        )

    return FileResponse(
        path=temp_path,
        filename=temp_filename,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
