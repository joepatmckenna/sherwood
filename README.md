# sherwood

# TODO
- leaderboard on home page
- buy/sell in units or dollars
- profile websocket, include price+value of things+usernames of investors
- no deposit/withdraw button, users start with $100,000
- inactivate buttons while awaiting response
- symbol price endpoint/socket, price quote on buy/sell form
- email verfication (smtplib, sendgrid)
- forgot password flow
- username input on sign up, ws for uniqueness validator
- broker_events table
- sell_all library fn?
- if (now - user.created_at) > T and not user.is_verified: block user until verified
- close connection to validate-password websocket after sign up successful or navigating away from page