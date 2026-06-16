# pyrefly: ignore [missing-import]
from PyPDF2 import PdfReader
from src.chunking import semantic_chunk

def get_pdf_text_with_metadata(pdf_docs):
    pdf_data = []
    for pdf in pdf_docs:
        doc_title = pdf.name.replace('.pdf', '')
        pdf_reader = PdfReader(pdf)
        for page_num, page in enumerate(pdf_reader.pages, 1):
            text = page.extract_text()
            if text and text.strip():
                pdf_data.append({
                    'text':        text,
                    'doc_title':   doc_title,
                    'page_number': page_num,
                    'doc_name':    pdf.name
                })
    return pdf_data


def get_text_chunks_semantic(pdf_data, model_name=None):
    chunks_with_metadata = []
    for item in pdf_data:
        chunks = semantic_chunk(item['text'], target_size=800, overlap_size=150)
        for chunk_idx, chunk in enumerate(chunks):
            if chunk.strip():
                summary = chunk[:150] + "..." if len(chunk) > 150 else chunk
                chunks_with_metadata.append({
                    'content':     chunk,
                    'doc_title':   item['doc_title'],
                    'page_number': item['page_number'],
                    'doc_name':    item['doc_name'],
                    'summary':     summary,
                    'chunk_id':    f"{item['doc_title']}_p{item['page_number']}_c{chunk_idx}"
                })
    return chunks_with_metadata
