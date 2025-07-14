# Dans app.py, remplacer cette ligne (autour de la ligne 120) :
# reply = generate_reply(selected_mail["body"], user_prompt)

# Par cette ligne :
reply = generate_reply(selected_mail["body"], user_prompt, selected_mail['db_id'])