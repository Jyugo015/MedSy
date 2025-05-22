from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

# --- LLM Setup ---
model_name = "mistralai/Mistral-7B-Instruct-v0.2"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map={"": 0}, 
    torch_dtype=torch.float16,
    load_in_8bit=True
)
# --- In-memory chat state ---
user_state = {}

def llm_reply(prompt):
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    output_ids = model.generate(
        **inputs, max_new_tokens=100,
        do_sample=False,
        pad_token_id=tokenizer.eos_token_id
    )
    text = tokenizer.decode(output_ids[0], skip_special_tokens=True)
    return text.split("Assistant:")[-1].strip()