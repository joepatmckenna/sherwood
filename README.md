# sherwood

models
- transactions table / broker_events table
- include portfolio cash as part of ownership percentage calculations

broker
- set price_delay=0 for buy/sell/invest/divest routes
- guardrails on funds with investors (max number of symbols, restrictions on selling most of portfolio/rugging)
- buy/sell in units or dollars
- sell_all library fn?

registrar
- email verfication (smtplib, sendgrid) / forgot password flow
- if (now - user.created_at) > T and not user.is_verified: block user until verified

ui
- inactivate buttons while awaiting response
- symbol price endpoint/socket, price quote on buy/sell form
- close connection to validator websocket after sign up successful or navigating away from page