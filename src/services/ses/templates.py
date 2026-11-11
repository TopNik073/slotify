import html

from typing import Protocol


class EmailTemplate(Protocol):
    """Protocol for email templates"""

    subject: str
    body: str
    html: bool = False

    def render(self) -> str:
        """Render template to string"""
        ...


class TwoFactorAuthTemplate:
    def __init__(self, code: str):
        self.subject = f'Your verification code: {code}'
        self.html = True
        self.body = f"""
        <html>
            <head>
                <title>Slotify Auth</title>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f0f4f8;
            ">
                <div style="
                    max-width: 600px;
                    margin: 40px auto;
                    padding: 30px;
                    background-color: #1E3A8A;
                    border-radius: 12px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                ">
                    <h1 style="
                        color: #FFFFFF;
                        margin-bottom: 24px;
                        font-size: 26px;
                        text-align: center;
                    ">Email Verification</h1>

                    <p style="
                        font-size: 16px;
                        color: #DBEAFE;
                        margin-bottom: 10px;
                    ">Welcome,</p>

                    <p style="
                        font-size: 16px;
                        color: #DBEAFE;
                        margin-bottom: 20px;
                    ">To complete your sign-in, use the verification code below:</p>

                    <div style="
                        background-color: #DBEAFE;
                        border-radius: 8px;
                        padding: 20px;
                        margin: 25px 0;
                        text-align: center;
                    ">
                        <code style="
                            font-size: 36px;
                            font-weight: bold;
                            letter-spacing: 6px;
                            font-family: 'Courier New', monospace;
                            color: #1E3A8A;
                        ">{code}</code>
                    </div>

                    <div style="
                        font-size: 14px;
                        color: #BFDBFE;
                        margin-top: 30px;
                        padding-top: 20px;
                        border-top: 1px solid rgba(255, 255, 255, 0.1);
                        line-height: 1.6;
                    ">
                        <p style="margin: 5px 0;">• This code will expire in 10 minutes.</p>
                        <p style="margin: 5px 0;">• If you didn't request this code, please ignore this email.</p>
                    </div>
                </div>
            </body>
        </html>
        """

    def render(self) -> str:
        """Render template to string"""
        return self.body


class RegistrationInvitationTemplate:
    """Account setup only: no meeting metadata for mail clients to turn into another event."""

    def __init__(
        self,
        organizer_name: str,
        registration_url: str,
    ):
        self.organizer_name = html.escape(organizer_name)
        self.registration_url = html.escape(registration_url, quote=True)

        self.subject = 'Завершите регистрацию в Slotify'
        self.html = True

    def render(self) -> str:
        return f"""
        <html lang="ru">
            <head>
                <title>Регистрация в Slotify</title>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f0f4f8;
            ">
                <div style="
                    max-width: 600px;
                    margin: 40px auto;
                    padding: 30px;
                    background-color: #1E3A8A;
                    border-radius: 12px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                ">
                    <h1 style="
                        color: #FFFFFF;
                        margin-bottom: 24px;
                        font-size: 26px;
                        text-align: center;
                    ">Добро пожаловать в Slotify</h1>

                    <p style="
                        font-size: 16px;
                        color: #DBEAFE;
                        margin-bottom: 20px;
                    "><strong style="color:#FFFFFF;">{self.organizer_name}</strong> добавил вас в Slotify.
                    Используйте этот адрес почты при регистрации, чтобы просматривать приглашения
                    и управлять своими встречами.</p>

                    <p style="text-align:center; margin: 30px 0;">
                        <a href="{self.registration_url}" style="
                            display: inline-block;
                            padding: 14px 28px;
                            background-color: #FFFFFF;
                            color: #1E3A8A;
                            font-weight: 600;
                            text-decoration: none;
                            border-radius: 8px;
                        ">Зарегистрироваться</a>
                    </p>

                    <div style="
                        font-size: 14px;
                        color: #BFDBFE;
                        margin-top: 30px;
                        padding-top: 20px;
                        border-top: 1px solid rgba(255, 255, 255, 0.1);
                        line-height: 1.6;
                    ">
                        <p style="margin: 5px 0;">
                            Если вы не планируете пользоваться Slotify, это письмо можно проигнорировать.
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """
