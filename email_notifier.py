# email_notifier.py
from typing import Optional

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from gcp_secrets import get_secret

SENDGRID_API_KEY = get_secret("SENDGRID_API_KEY", required=False)
FROM_EMAIL = get_secret("NOTIFY_FROM", default="no-reply@example.com", required=False)
ADMIN_EMAIL = get_secret("ADMIN_EMAIL", default="hr@example.com", required=False)


def _send_email(to_email: str, subject: str, html_content: str) -> bool:
    if not SENDGRID_API_KEY:
        print("[email_notifier] SENDGRID_API_KEY missing; skipping email.")
        return False

    if not to_email:
        print("[email_notifier] No recipient email configured; skipping email.")
        return False

    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=to_email,
        subject=subject,
        html_content=html_content
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        resp = sg.send(message)
        print("Email sent, status:", resp.status_code)
        return True
    except Exception as e:
        print("SendGrid error:", e)
        return False


def send_pass_notification(candidate_name: str, candidate_email: str, job_title: str, score: float, status: str = "passed", recipient_email: Optional[str] = None):
    to_email = recipient_email or ADMIN_EMAIL
    status_label = status.title()
    html_content = (
        f"<p>Candidate <strong>{candidate_name}</strong> ({candidate_email}) completed the assessment for "
        f"<strong>{job_title}</strong>.</p>"
        f"<p>Score: <strong>{score}%</strong> — Status: <strong>{status_label}</strong>.</p>"
    )
    return _send_email(to_email, f"Candidate assessment result: {candidate_name} — {job_title}", html_content)


def send_candidate_notification(candidate_name: str, candidate_email: str, job_title: str, score: float, status: str = "passed"):
    if not candidate_email:
        return False

    status_label = status.title()
    if status.lower() == "passed":
        body = (
            f"<p>Hi {candidate_name},</p>"
            f"<p>Thank you for taking the assessment for <strong>{job_title}</strong>. Congratulations — you passed with a score of <strong>{score}%</strong>!"\
            " We will review your submission and get back to you soon.</p>"
            "<p>Best regards,<br/>Recruitment Team</p>"
        )
    else:
        body = (
            f"<p>Hi {candidate_name},</p>"
            f"<p>Thank you for completing the assessment for <strong>{job_title}</strong>. Your score was <strong>{score}%</strong>."\
            " Our team will review your submission and follow up if there is a good fit.</p>"
            "<p>Best regards,<br/>Recruitment Team</p>"
        )

    return _send_email(candidate_email, f"Assessment result: {job_title}", body)
