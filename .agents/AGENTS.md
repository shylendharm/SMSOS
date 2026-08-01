# Workspace Behavioral Rules & Customizations

## Webhook & Message Delivery Diagnostics Checklist
Whenever the user reports that WhatsApp/SMS messages are not reaching the backend or no logs appear:
1. **Check Localtunnel URL**: Verify if localtunnel restarted and generated a new domain or if static subdomain (`smsos-app-dev.loca.lt`) is being used.
2. **Check Localtunnel Interstitial Warning**: Remind/verify if Localtunnel `loca.lt` interstitial landing page requires opening in browser to pass POST webhooks.
3. **Check Webhook Endpoint Path & Credentials**:
   - Ensure the Twilio webhook URL ends with `/api/v1/webhooks/twilio` and method is `HTTP POST`.
   - Ensure `TWILIO_PHONE_NUMBER` in `.env` is set to `+14155238886` (Twilio WhatsApp Sandbox channel number).
