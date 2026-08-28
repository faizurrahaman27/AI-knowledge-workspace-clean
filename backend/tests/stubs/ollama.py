def chat(model, messages, stream=False, options=None):
    if stream:
        def gen():
            yield {"message": {"content": "stub answer"}}
        return gen()
    return {"message": {"content": "stub answer"}}

def _extra_chat(*a, **k): pass

_ORIGINAL_CHAT = chat

def chat(model, messages, stream=False, options=None, **kwargs):
    content = messages[0]["content"] if messages else ""
    if "mind map" in content.lower() or "Return ONLY valid JSON" in content:
        text = '{"title": "Root", "children": [{"title": "A", "children": []}, {"title": "B", "children": []}]}'
    elif "Classify this user request" in content:
        text = "summary"
    else:
        text = "stub answer"
    if stream:
        def gen():
            yield {"message": {"content": text}}
        return gen()
    return {"message": {"content": text}}
