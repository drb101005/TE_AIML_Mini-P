import fitz
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from services.tree_builder import build_document_tree


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


async def extract_pdf_pages(file: UploadFile) -> list[dict[str, object]]:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Only PDF files are accepted.")

    pdf_bytes = await file.read()

    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except fitz.FileDataError as error:
        raise HTTPException(
            status_code=400, detail="The uploaded file is not a valid PDF."
        ) from error

    try:
        pages = [
            {"page": page_number, "text": page.get_text()}
            for page_number, page in enumerate(document, start=1)
        ]
    finally:
        document.close()

    return pages


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)) -> dict[str, object]:
    pages = await extract_pdf_pages(file)
    return {"filename": file.filename, "pages": pages}


@app.post("/upload/tree")
async def upload_pdf_tree(file: UploadFile = File(...)) -> dict[str, object]:
    pages = await extract_pdf_pages(file)
    return {"filename": file.filename, "tree": build_document_tree(pages)}
