"""Envio do código 2FA por SMTP (stdlib).

Configure via variáveis de ambiente ou arquivo .env na raiz do projeto (veja env.example).
"""

from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.mime.text import MIMEText


def _env_bool(key: str, default: str = "0") -> bool:
    return (os.environ.get(key, default) or default).lower() in ("1", "true", "yes", "on")


def send_2fa_code(to_addr: str, code: str, logger: logging.Logger | None = None) -> tuple[bool, str | None]:
    """
    Retorna (email_enviado, mensagem_opcional).
    Se SMTP não estiver configurado, registra o código no log (modo desenvolvimento).
    """
    log = logger or logging.getLogger(__name__)
    host = (os.environ.get("SMTP_HOST") or "").strip()
    port = int(os.environ.get("SMTP_PORT", "587") or "587")
    user = (os.environ.get("SMTP_USER") or "").strip()
    password = os.environ.get("SMTP_PASSWORD") or ""
    from_addr = (os.environ.get("SMTP_FROM") or user or "").strip()
    # STARTTLS em 587 (padrão Gmail / Outlook); SSL implícito em 465
    use_implicit_ssl = _env_bool("SMTP_SSL") or port == 465
    use_starttls = not use_implicit_ssl and _env_bool("SMTP_TLS", "1")

    if not host:
        log.warning("SMTP_HOST não definido — código 2FA para %s: %s", to_addr, code)
        return False, "E-mail não configurado no servidor; o código foi registrado no log."

    if not from_addr:
        log.error("SMTP_FROM ou SMTP_USER é obrigatório quando SMTP_HOST está definido.")
        return False, "Remetente (SMTP_FROM) não configurado no servidor."

    if not user:
        log.error("SMTP_USER é obrigatório para autenticar no SMTP.")
        return False, "Conta SMTP (SMTP_USER) não configurada no servidor."

    body = (
        f"Seu código de verificação AuroraYt: {code}\n\n"
        "Ele vale por 10 minutos. Se você não pediu este código, ignore este e-mail.\n"
    )

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = "Código de verificação — AuroraYt"
    msg["From"] = from_addr
    msg["To"] = to_addr
    raw = msg.as_string()

    ctx = ssl.create_default_context()

    try:
        if use_implicit_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=60, context=ctx) as smtp:
                smtp.login(user, password)
                smtp.sendmail(from_addr, [to_addr], raw)
        else:
            with smtplib.SMTP(host, port, timeout=60) as smtp:
                smtp.ehlo()
                if use_starttls:
                    smtp.starttls(context=ctx)
                    smtp.ehlo()
                smtp.login(user, password)
                smtp.sendmail(from_addr, [to_addr], raw)
    except smtplib.SMTPAuthenticationError:
        log.exception("Falha de autenticação SMTP (usuário/senha ou política do provedor).")
        return False, "Falha ao autenticar no servidor de e-mail. Confira SMTP_USER e SMTP_PASSWORD."
    except smtplib.SMTPException:
        log.exception("Erro SMTP ao enviar 2FA.")
        return False, "O servidor de e-mail recusou o envio. Confira SMTP_FROM e limites da conta."
    except OSError:
        log.exception("Falha de rede ao enviar e-mail 2FA.")
        return False, "Não foi possível conectar ao servidor de e-mail. Confira SMTP_HOST e SMTP_PORT."

    log.info("Código 2FA enviado por e-mail para %s", to_addr)
    return True, None
