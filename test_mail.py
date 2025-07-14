from mail_utils import get_emails_since

def test_fetch_emails():
    emails = get_emails_since()  # sans filtre date, ça récupère les derniers mails (max 100)
    print(f"Nombre de mails récupérés: {len(emails)}")
    for mail in emails[:5]:  # affiche les 5 premiers pour contrôle
        print(f"Objet: {mail['subject']} - Date: {mail['date']}")

if __name__ == "__main__":
    test_fetch_emails()
