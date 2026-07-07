Downloader de videos do yt sem direitos autorais ;)

## Conta e 2FA por e-mail

1. Acesse `/login.html`, crie uma conta e entre. Após a senha, o servidor envia um **código de 6 dígitos** para o seu e-mail.
2. Variáveis importantes:
   - **`SECRET_KEY`**: recomendada em qualquer ambiente “real”; se não existir, o servidor sobe com chave de desenvolvimento e avisa no terminal. Com **`PRODUCTION=1`**, `SECRET_KEY` passa a ser obrigatória.
   - **E-mail 2FA**: copie `env.example` para **`.env`** na raiz do projeto e preencha `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`. Instale dependências com `pip install -r requirements.txt` (inclui `python-dotenv`, que carrega o `.env` automaticamente). **Gmail** exige [senha de app](https://support.google.com/accounts/answer/185833), não a senha normal da conta. Sem `SMTP_HOST`, o código continua só no **log** do servidor.
3. Banco local: pasta `data/aurorayt_auth.db` (já ignorada no `.gitignore`).

Rotas `/api/download` e `/api/progress` exigem sessão autenticada (cookie).
