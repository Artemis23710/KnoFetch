import re

def split_into_sentences(text):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def semantic_chunk(text, target_size=800, overlap_size=150):
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    for paragraph in paragraphs:
        if not paragraph.strip():
            continue
        sentences = split_into_sentences(paragraph)
        for sentence in sentences:
            test_chunk = (current_chunk + " " + sentence).strip()
            if len(test_chunk) > target_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk = test_chunk
        if current_chunk:
            current_chunk += "\n"
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    return chunks


def create_parent_chunk_map(chunks_with_metadata):
    return {
        chunk['chunk_id']: {
            'full_content': chunk['content'],
            'summary':      chunk['summary'],
            'page_number':  chunk['page_number'],
            'doc_title':    chunk['doc_title'],
            'doc_name':     chunk['doc_name']
        }
        for chunk in chunks_with_metadata
    }


def expand_chunk_with_context(chunk_id, parent_map):
    if chunk_id not in parent_map:
        return None
    return parent_map[chunk_id]['full_content']
