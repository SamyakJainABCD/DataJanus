import json
import os
from enum import Enum
from typing import Literal

from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from google import genai
from google.genai import types
from pydantic import BaseModel, Field


def home(request):
    return render(request, 'main/home.html')


class AllowedType(str, Enum):
    IMAGE_DATA = "ImageData"
    ARRAY_BUFFER = "ArrayBuffer"
    FILE = "File"
    NUMBER = "Number"
    BOOLEAN = "Boolean"
    STRING = "String"
    JSON_OBJECT = "JSONObject"


class IODefinition(BaseModel):
    type: AllowedType = Field(
        description="Data type MUST be selected strictly from the allowed type enum."
    )
    count: Literal["1", "*"] = Field(
        description="Use '1' for a single value or '*' for a variable-length array."
    )
    name: str = Field(
        description="Valid, camelCase JavaScript variable name to use inside code_snippet."
    )


class NodePipelineResponse(BaseModel):
    inputs: list[IODefinition] = Field(description="Required input parameters.")
    outputs: list[IODefinition] = Field(description="Expected output results.")
    code_snippet: str = Field(
        description="Standalone vanilla JS code converting inputs to outputs."
    )


SYSTEM_INSTRUCTION = f"""
You are a deterministic code compilation engine.
Your task is to analyze user requests and output a JSON execution node.
return the input, output and javascript code snippet required to perform the action specified in the prompt.
The code snippet will not contain the logic for input and output and assume input is already 
there in variables with the names you specified, and leave the output in variables with the 
names you specified.

RULES:
1. `type` for inputs and outputs MUST be selected strictly from this list:
   {[t.value for t in AllowedType]}
2. `count` must be either "1" or "*". `"1"` means a single value; `"*"` means an array of values.
3. `name` must be a valid camelCase JavaScript identifier.
4. `code_snippet` must be pure vanilla JS that takes input variable `name`s and assigns the result to output variable `name`s.
5. ASYNC CONTEXT: The `code_snippet` runs inside an `async () => {{ ... }}` block. You can and should use `await` where necessary.
6. ARRAY SEMANTICS: If `count == "*"`, the runtime variable is an array and must be treated like an array in the generated JavaScript code. Do not treat it as a string or single object.
7. IMAGE DATA HANDLING: If an input or output type is `ImageData`, the runtime variable will actually be a **Base64 Data URL string**, NOT an `ImageData` object.
   - To read an image: You MUST create an `Image()`, assign the string to `img.src`, `await` its `onload` event wrapped in a Promise, and draw it to a `<canvas>` to manipulate pixels.
   - To output an image: You MUST convert your manipulated canvas back to a string using `canvas.toDataURL()` and assign that string to the output variable.
"""

# for testing
# def generate_processing_node(user_prompt: str):
#     return '{"inputs": [{"type": "String", "count": "1", "name": "inputText"}], "outputs": [{"type": "String", "count": "1", "name": "outputText"}], "code_snippet": "outputText = inputText.replace(/(\\r\\n|\\n|\\r)/gm, \'\');"}'
#     return '{"inputs": [{"type": "String", "count": "1", "name": "inputText"}], "outputs": [{"type": "String", "count": "1", "name": "outputText"}], "code_snippet": "outputText = inputText.replace(/,/g, \'\');"}'

def generate_processing_node(user_prompt: str):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    client = genai.Client(api_key=api_key)

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        response_mime_type="application/json",
        response_schema=NodePipelineResponse,
        temperature=0.1,
    )

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=user_prompt,
        config=config,
    )
    return response.text


# make sure IO types are valid
def _normalize_type(io_type):
    value = str(io_type or "String")
    try:
        return AllowedType(value)
    except ValueError:
        return AllowedType.STRING


def _get_ui_variant(io_type):
    normalized = _normalize_type(io_type)
    if normalized == AllowedType.IMAGE_DATA:
        return "image"
    return "string"


def _build_generated_app_html(request, node_payload):
    if not node_payload:
        return HttpResponse("<html><body><h1>Generated App</h1><p>No valid app definition was returned.</p></body></html>")

    inputs = node_payload.get('inputs', []) or []
    outputs = node_payload.get('outputs', []) or []
    code_snippet = node_payload.get('code_snippet', '') or ''

    rendered_inputs = []
    for item in inputs:
        item_type = item.get('type', AllowedType.STRING.value)
        field_name = str(item.get('name', 'inputValue'))
        item_count = str(item.get('count', '1'))
        rendered_inputs.append(
            render_to_string(
                f'main/partials/{_get_ui_variant(item_type)}_input.html',
                {'input': {'name': field_name, 'type': item_type, 'count': item_count}},
            )
        )

    rendered_outputs = []
    for item in outputs:
        item_type = item.get('type', AllowedType.STRING.value)
        field_name = str(item.get('name', 'outputValue'))
        item_count = str(item.get('count', '1'))
        rendered_outputs.append(
            render_to_string(
                f'main/partials/{_get_ui_variant(item_type)}_output.html',
                {'output': {'name': field_name, 'type': item_type, 'count': item_count}},
            )
        )

    context = {
        'inputs': inputs,
        'outputs': outputs,
        'inputs_json': json.dumps(inputs),
        'outputs_json': json.dumps(outputs),
        'rendered_inputs': '\n'.join(rendered_inputs),
        'rendered_outputs': '\n'.join(rendered_outputs),
        'code_snippet': code_snippet,
    }
    return render(request, 'main/generated_app.html', context)


def makeApp(request):
    if request.method != 'POST':
        return HttpResponse('This view only accepts POST requests.', status=405)

    user_prompt = request.POST.get('user_prompt', '')
    if user_prompt == '':
        return HttpResponse('prompt cannot be empty.')

    try:
        raw_response = generate_processing_node(user_prompt=user_prompt)
    except RuntimeError as exc:
        return HttpResponse(str(exc), status=500)
    except Exception:
        return HttpResponse('The app generator could not process your request. Please try again.', status=500)
    print(raw_response)
    if not raw_response:
        node_payload = {}
    else:
        node_payload = json.loads(raw_response)
    return _build_generated_app_html(request, node_payload)
