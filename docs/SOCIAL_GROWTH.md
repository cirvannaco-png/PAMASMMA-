# PAMASMMA Social Growth Subsystem

PAMASMMA v4.2 adds a provider-neutral social execution layer. The cognitive systems remain responsible for strategy, audience interpretation, narrative, persuasion governance and decision quality; the social subsystem is responsible for external platform execution and outcome collection.

## Control flow

intent -> cognitive decision -> platform adapter -> publish/listen/reply/measure -> social memory -> learning

Advertising uses an explicit safety boundary:

campaign plan -> persisted approval state -> provider execution

There is no autonomous ad spending by default. The API exposes approval as the execution gate.

## Supported platform boundary

| Platform | Account connection | Publish | Engagement | Analytics | Ads |
|---|---|---|---|---|---|
| Facebook | Yes | Yes | Yes | Yes | Yes |
| Instagram | Yes | Media | Comments | Insights | Meta account boundary |
| TikTok | Yes | Video/photo boundary | Adapter-limited | Adapter-limited | Not enabled |
| YouTube | Yes | Video upload | Comments/replies | YouTube Analytics | Not enabled |
| LinkedIn | Yes | Yes | Comments | Adapter boundary | Read boundary |
| X | Yes | Posts/replies | Mentions/recent search | Adapter boundary | Not enabled |
| Threads | Yes | Yes | Replies/comments boundary | Adapter boundary | Not enabled |
| Pinterest | Yes | Pins | Read boundary | Organic analytics boundary | Supported capability boundary |
| Reddit | Yes | Submissions | Comments | Adapter-limited | Not enabled |
| Telegram | Bot token | Messages | Bot-channel boundary | Adapter-limited | N/A |
| WhatsApp | Business token | Messages | Messaging boundary | N/A | N/A |

A platform being listed does not mean PAMASMMA can bypass platform approval, review, account-role restrictions, API quotas or policy requirements. Those are external controls and remain visible to the operator.

## API

- GET /api/v1/social/platforms
- GET /api/v1/social/oauth/{platform}/start
- GET /api/v1/social/oauth/{platform}/callback
- POST /api/v1/social/accounts/manual
- GET /api/v1/social/accounts
- DELETE /api/v1/social/accounts/{account_id}
- POST /api/v1/social/publish
- POST /api/v1/social/engagement/sync/{account_id}
- GET /api/v1/social/engagement
- POST /api/v1/social/engagement/reply
- POST /api/v1/social/campaigns
- POST /api/v1/social/campaigns/{campaign_id}/approve
- POST /api/v1/social/scheduled/process

## Security

OAuth state is single-use and stored in the existing Redis cache. Access and refresh tokens are encrypted using the application's AES-256-GCM mechanism before persistence. Plain credentials must never be committed.

## Operator workflow

1. Configure only the platforms you intend to connect.
2. Run alembic upgrade head to apply migration 007_social_growth.
3. Open /social, connect an account, and verify capabilities.
4. Test publishing on a sandbox/private target before public distribution.
5. Synchronize engagement and verify classification/escalation behavior.
6. Create ad plans first. Approve only campaigns you deliberately want executed.

## External API notes

Capabilities differ materially by platform. TikTok Direct Post has review/audit requirements for normal public visibility; YouTube comments can be read and replied to through the Data API; LinkedIn's current Posts API and social-actions API support publishing and comments; Pinterest exposes organic content, analytics and ads APIs with access-tier controls. PAMASMMA models capabilities explicitly rather than pretending every platform exposes the same operations.
