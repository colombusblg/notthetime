import openai
import tiktoken  # si tu ne l'as pas, installe avec `pip install tiktoken`

def truncate_text(text, max_tokens=3000):
    enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
    tokens = enc.encode(text)
    if len(tokens) > max_tokens:
        tokens = tokens[:max_tokens]
    return enc.decode(tokens)

def summarize_emails(mails):
    full_text = "\n\n".join(mail['body'] for mail in mails)
    truncated_text = truncate_text(full_text, max_tokens=3000)  # limite à 3000 tokens

    messages = [
        {"role": "system", "content": "Tu es un assistant qui résume des mails."},
        {"role": "user", "content": f"Voici les mails à résumer :\n{truncated_text}"}
    ]

    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=1000,
    )
    return response.choices[0].message.content

def generate_reply(email_body, prompt):
    messages = [
        {"role": "system", "content": "Tu es un assistant qui aide à rédiger des emails professionnels."},
        {"role": "user", "content": f"Voici un mail reçu :\n{email_body}\n\nJe souhaite répondre avec cette intention :\n{prompt}"}
    ]

    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=700,
    )

    return response.choices[0].message.content.strip()
