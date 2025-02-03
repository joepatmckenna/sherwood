# sherwood

broker
- guardrails on funds with investors (max number of symbols, restrictions on selling most of portfolio/rugging)
- buy/sell in units or dollars
- sell_all library fn?
- sell: remove holding if value < 0.01

registrar
- email verfication (smtplib, sendgrid) / forgot password flow
- if (now - user.created_at) > T and not user.is_verified: block user until verified

ui
- inactivate buttons while awaiting response
- symbol price endpoint/socket, price quote on buy/sell form
- close connection to validator websocket after sign up successful or navigating away from page



make sign out GET
