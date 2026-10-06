"use client";

import { useEffect, useState, type CSSProperties } from "react";
import toast from "react-hot-toast";

import { social } from "@/lib/api";

type Account = {
  id: string;
  platform: string;
  external_account_id: string;
  display_name?: string | null;
  status: string;
  capabilities: string[];
};

type PlatformInfo = {
  platform: string;
  capabilities: string[];
};

type Engagement = {
  id: string;
  account_id: string;
  platform: string;
  item_id: string;
  text?: string | null;
  intent?: string | null;
  sentiment?: string | null;
  priority: string;
  author_name?: string | null;
};

type Tab = "accounts" | "publish" | "engagement" | "analytics" | "ads";

const PLATFORM_LABELS: Record<string, string> = {
  facebook: "Facebook",
  instagram: "Instagram",
  tiktok: "TikTok",
  youtube: "YouTube",
  linkedin: "LinkedIn",
  x: "X",
  threads: "Threads",
  pinterest: "Pinterest",
  reddit: "Reddit",
  telegram: "Telegram",
  whatsapp: "WhatsApp",
};

const MANUAL_PLATFORMS = new Set(["telegram", "whatsapp"]);

const field: CSSProperties = {
  width: "100%",
  boxSizing: "border-box",
  background: "#070711",
  color: "#DDDDF0",
  padding: 11,
  borderRadius: 8,
  border: "1px solid #26263F",
  marginBottom: 10,
  fontSize: 12,
};

const card: CSSProperties = {
  background: "#0A0A18",
  border: "1px solid #1A1A32",
  borderRadius: 14,
  padding: 18,
};

export function SocialCommandCenter() {
  const [platforms, setPlatforms] = useState<PlatformInfo[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [engagement, setEngagement] = useState<Engagement[]>([]);
  const [selectedAccount, setSelectedAccount] = useState("");
  const [text, setText] = useState("");
  const [mediaUrl, setMediaUrl] = useState("");
  const [title, setTitle] = useState("");
  const [scheduledAt, setScheduledAt] = useState("");
  const [reply, setReply] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<Tab>("accounts");
  const [analytics, setAnalytics] = useState<Record<string, unknown> | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [manualOpen, setManualOpen] = useState(false);
  const [manual, setManual] = useState({
    platform: "telegram",
    accessToken: "",
    refreshToken: "",
    externalAccountId: "",
    displayName: "",
  });
  const [campaign, setCampaign] = useState({
    name: "",
    objective: "OUTCOME_TRAFFIC",
    dailyBudget: "",
    currency: "USD",
    adAccountId: "",
  });
  const [plannedCampaignId, setPlannedCampaignId] = useState("");

  const refresh = async () => {
    const [platformData, accountData, engagementData] = await Promise.all([
      social.platforms(),
      social.accounts(),
      social.engagement(),
    ]);
    setPlatforms(platformData.platforms);
    setAccounts(accountData.accounts);
    setEngagement(
      engagementData.items.map((item) => ({
        id: String(item.id ?? ""),
        account_id: String(item.account_id ?? ""),
        platform: String(item.platform ?? ""),
        item_id: String(item.item_id ?? ""),
        text: typeof item.text === "string" ? item.text : null,
        intent: typeof item.intent === "string" ? item.intent : null,
        sentiment: typeof item.sentiment === "string" ? item.sentiment : null,
        priority: String(item.priority ?? "normal"),
        author_name:
          typeof item.author_name === "string" ? item.author_name : null,
      })),
    );
  };

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const [platformData, accountData, engagementData] = await Promise.all([
          social.platforms(),
          social.accounts(),
          social.engagement(),
        ]);

        if (cancelled) return;

        setPlatforms(platformData.platforms);
        setAccounts(accountData.accounts);
        setEngagement(
          engagementData.items.map((item) => ({
            id: String(item.id ?? ""),
            account_id: String(item.account_id ?? ""),
            platform: String(item.platform ?? ""),
            item_id: String(item.item_id ?? ""),
            text: typeof item.text === "string" ? item.text : null,
            intent: typeof item.intent === "string" ? item.intent : null,
            sentiment:
              typeof item.sentiment === "string" ? item.sentiment : null,
            priority: String(item.priority ?? "normal"),
            author_name:
              typeof item.author_name === "string"
                ? item.author_name
                : null,
          })),
        );

        if (accountData.accounts[0]) {
          setSelectedAccount(accountData.accounts[0].id);
        }
      } catch {
        if (!cancelled) {
          toast.error("Unable to load social control plane");
        }
      }
    };

    void load();

    return () => {
      cancelled = true;
    };
  }, []);

  const selected = accounts.find((account) => account.id === selectedAccount);

  const connect = async (platform: string) => {
    if (MANUAL_PLATFORMS.has(platform)) {
      setManual((value) => ({ ...value, platform }));
      setManualOpen(true);
      setTab("accounts");
      return;
    }

    try {
      const result = await social.oauthStart(platform);
      window.location.assign(result.authorization_url);
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "OAuth is not configured",
      );
    }
  };

  const saveManualAccount = async () => {
    if (
      !manual.accessToken.trim() ||
      !manual.externalAccountId.trim() ||
      !manual.platform
    ) {
      toast.error("Platform, token and external account ID are required");
      return;
    }

    setLoading(true);
    try {
      await social.manualAccount({
        platform: manual.platform,
        access_token: manual.accessToken.trim(),
        refresh_token: manual.refreshToken.trim() || undefined,
        external_account_id: manual.externalAccountId.trim(),
        display_name: manual.displayName.trim() || undefined,
      });
      toast.success("Social account connected");
      setManualOpen(false);
      setManual((value) => ({
        ...value,
        accessToken: "",
        refreshToken: "",
        externalAccountId: "",
        displayName: "",
      }));
      await refresh();
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Account connection failed",
      );
    } finally {
      setLoading(false);
    }
  };

  const publish = async () => {
    if (!selectedAccount || !text.trim()) {
      toast.error("Select an account and enter content");
      return;
    }

    setLoading(true);
    try {
      await social.publish({
        command: {
          account_id: selectedAccount,
          text: text.trim(),
          ...(mediaUrl ? { media_url: mediaUrl } : {}),
          ...(title ? { title } : {}),
        },
        ...(scheduledAt
          ? { scheduled_at: new Date(scheduledAt).toISOString() }
          : {}),
      });
      toast.success(scheduledAt ? "Post queued" : "Published");
      setText("");
      setMediaUrl("");
      setTitle("");
      setScheduledAt("");
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Publishing failed",
      );
    } finally {
      setLoading(false);
    }
  };

  const sync = async (accountId: string) => {
    try {
      const result = await social.sync(accountId);
      toast.success(`${result.count} engagement items synchronized`);
      await refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Sync failed");
    }
  };

  const sendReply = async (item: Engagement) => {
    const body = reply[item.id]?.trim();

    if (!body) return;

    try {
      await social.reply({
        account_id: item.account_id,
        item_id: item.item_id,
        text: body,
      });
      toast.success("Reply sent");
      setReply((value) => ({ ...value, [item.id]: "" }));
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Reply failed");
    }
  };

  const loadAnalytics = async () => {
    if (!selectedAccount) {
      toast.error("Select an account first");
      return;
    }

    setAnalyticsLoading(true);

    try {
      const result = await social.analytics(selectedAccount);
      setAnalytics(result);
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Analytics unavailable",
      );
    } finally {
      setAnalyticsLoading(false);
    }
  };

  const planAd = async () => {
    if (!selectedAccount || !campaign.name.trim()) {
      toast.error("Select an account and name the campaign");
      return;
    }

    if (!selected?.capabilities.includes("ads_write")) {
      toast.error("The selected platform does not expose ad creation.");
      return;
    }

    try {
      const result = await social.planCampaign({
        account_id: selectedAccount,
        ad_account_id: campaign.adAccountId || undefined,
        name: campaign.name,
        objective: campaign.objective,
        daily_budget: campaign.dailyBudget
          ? Number(campaign.dailyBudget)
          : undefined,
        currency: campaign.currency,
      });
      setPlannedCampaignId(result.campaign_id);
      toast.success("Campaign planned — explicit approval is still required");
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Campaign planning failed",
      );
    }
  };

  const approveAd = async () => {
    if (!plannedCampaignId) {
      toast.error("Plan a campaign first");
      return;
    }

    try {
      const result = await social.approveCampaign(plannedCampaignId);
      toast.success(
        result.external_campaign_id
          ? "Campaign created"
          : "Campaign approval completed",
      );
      setPlannedCampaignId("");
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Campaign approval failed",
      );
    }
  };

  return (
    <main
      style={{
        minHeight: "100vh",
        background: "#04040D",
        color: "#DDE0F0",
        padding: 24,
        fontFamily: "Inter, system-ui, sans-serif",
      }}
    >
      <header
        style={{
          maxWidth: 1180,
          margin: "0 auto 24px",
          display: "flex",
          justifyContent: "space-between",
          gap: 16,
          alignItems: "center",
        }}
      >
        <div>
          <div style={{ fontSize: 10, letterSpacing: 3, color: "#6B3FFB" }}>
            PAMASMMA / SOCIAL GROWTH
          </div>
          <h1 style={{ fontSize: 28, margin: "6px 0" }}>
            Social Command Center
          </h1>
          <div style={{ color: "#66668C", fontSize: 12 }}>
            Connect, publish, listen, respond, measure and govern campaigns
            from one control plane.
          </div>
        </div>

        <div
          style={{
            fontSize: 10,
            color: "#55D6BE",
            border: "1px solid #1D5048",
            borderRadius: 99,
            padding: "7px 11px",
          }}
        >
          ADS REQUIRE APPROVAL
        </div>
      </header>

      <nav
        style={{
          maxWidth: 1180,
          margin: "0 auto 18px",
          display: "flex",
          gap: 8,
          flexWrap: "wrap",
        }}
      >
        {(
          ["accounts", "publish", "engagement", "analytics", "ads"] as Tab[]
        ).map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => setTab(item)}
            style={{
              background: tab === item ? "#181432" : "#0A0A18",
              color: tab === item ? "#E8E8FA" : "#66668C",
              border: "1px solid #1A1A32",
              borderRadius: 9,
              padding: "9px 13px",
              fontSize: 11,
              textTransform: "uppercase",
            }}
          >
            {item}
          </button>
        ))}
      </nav>

      <section style={{ maxWidth: 1180, margin: "0 auto" }}>
        {tab === "accounts" && (
          <>
            <div
              style={{
                display: "grid",
                gridTemplateColumns:
                  "repeat(auto-fit,minmax(210px,1fr))",
                gap: 10,
              }}
            >
              {platforms.map((platform) => {
                const manualPlatform = MANUAL_PLATFORMS.has(platform.platform);

                return (
                  <div key={platform.platform} style={card}>
                    <div style={{ fontWeight: 700 }}>
                      {PLATFORM_LABELS[platform.platform] ?? platform.platform}
                    </div>
                    <div
                      style={{
                        color: "#55557C",
                        fontSize: 10,
                        margin: "7px 0 12px",
                        lineHeight: 1.5,
                      }}
                    >
                      {platform.capabilities.join(" · ")}
                    </div>
                    <button
                      type="button"
                      onClick={() => void connect(platform.platform)}
                      style={{
                        width: "100%",
                        background: "#12112B",
                        border: "1px solid #29234D",
                        color: "#B6A6FF",
                        padding: "8px 10px",
                        borderRadius: 8,
                      }}
                    >
                      {manualPlatform ? "Configure" : "Connect"}
                    </button>
                  </div>
                );
              })}
            </div>

            {manualOpen && (
              <div style={{ ...card, marginTop: 12, maxWidth: 760 }}>
                <div
                  style={{
                    fontSize: 10,
                    color: "#6B3FFB",
                    letterSpacing: 2,
                    marginBottom: 12,
                  }}
                >
                  MANUAL BUSINESS / BOT CONNECTION
                </div>
                <select
                  value={manual.platform}
                  onChange={(event) =>
                    setManual((value) => ({
                      ...value,
                      platform: event.target.value,
                    }))
                  }
                  style={field}
                >
                  <option value="telegram">Telegram</option>
                  <option value="whatsapp">WhatsApp</option>
                </select>
                <input
                  value={manual.accessToken}
                  onChange={(event) =>
                    setManual((value) => ({
                      ...value,
                      accessToken: event.target.value,
                    }))
                  }
                  placeholder="Access / bot token"
                  type="password"
                  style={field}
                  autoComplete="off"
                />
                <input
                  value={manual.refreshToken}
                  onChange={(event) =>
                    setManual((value) => ({
                      ...value,
                      refreshToken: event.target.value,
                    }))
                  }
                  placeholder="Refresh token (when applicable)"
                  type="password"
                  style={field}
                  autoComplete="off"
                />
                <input
                  value={manual.externalAccountId}
                  onChange={(event) =>
                    setManual((value) => ({
                      ...value,
                      externalAccountId: event.target.value,
                    }))
                  }
                  placeholder="Chat / business account ID"
                  style={field}
                />
                <input
                  value={manual.displayName}
                  onChange={(event) =>
                    setManual((value) => ({
                      ...value,
                      displayName: event.target.value,
                    }))
                  }
                  placeholder="Display name"
                  style={field}
                />
                <div style={{ display: "flex", gap: 8 }}>
                  <button
                    type="button"
                    disabled={loading}
                    onClick={() => void saveManualAccount()}
                    style={{
                      background: "#6B3FFB",
                      color: "white",
                      border: 0,
                      borderRadius: 9,
                      padding: "10px 15px",
                      fontWeight: 700,
                    }}
                  >
                    Save Connection
                  </button>
                  <button
                    type="button"
                    onClick={() => setManualOpen(false)}
                    style={{
                      background: "#12121F",
                      color: "#8D8DAA",
                      border: "1px solid #2B2B48",
                      borderRadius: 9,
                      padding: "10px 15px",
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            <div style={{ marginTop: 12 }}>
              {accounts.length === 0 ? (
                <div
                  style={{
                    padding: 18,
                    border: "1px dashed #242444",
                    borderRadius: 12,
                    color: "#59597D",
                    fontSize: 12,
                  }}
                >
                  No social accounts connected yet.
                </div>
              ) : (
                accounts.map((account) => (
                  <div
                    key={account.id}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      gap: 12,
                      padding: 12,
                      marginBottom: 7,
                      background: "#0A0A18",
                      border: "1px solid #1A1A32",
                      borderRadius: 10,
                    }}
                  >
                    <div>
                      <b>
                        {PLATFORM_LABELS[account.platform] ?? account.platform}
                      </b>
                      <div style={{ fontSize: 10, color: "#5C5C82" }}>
                        {account.display_name ?? account.external_account_id} ·{" "}
                        {account.status}
                      </div>
                    </div>
                    <div style={{ display: "flex", gap: 8 }}>
                      <button
                        type="button"
                        onClick={() => setSelectedAccount(account.id)}
                        style={{
                          padding: "7px 9px",
                          background:
                            selectedAccount === account.id
                              ? "#241D42"
                              : "#12121F",
                          color: "#DDE0F0",
                          border: "1px solid #2B2850",
                          borderRadius: 7,
                          fontSize: 10,
                        }}
                      >
                        Use
                      </button>
                      <button
                        type="button"
                        onClick={() => void sync(account.id)}
                        style={{
                          padding: "7px 9px",
                          background: "#101A19",
                          color: "#78DCCB",
                          border: "1px solid #21443F",
                          borderRadius: 7,
                          fontSize: 10,
                        }}
                      >
                        Sync
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </>
        )}

        {tab === "publish" && (
          <div style={{ ...card, maxWidth: 760 }}>
            <div
              style={{ fontSize: 10, color: "#68688D", marginBottom: 8 }}
            >
              ACCOUNT
            </div>
            <select
              value={selectedAccount}
              onChange={(event) => setSelectedAccount(event.target.value)}
              style={field}
            >
              <option value="">Select account</option>
              {accounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {PLATFORM_LABELS[account.platform]} —{" "}
                  {account.display_name ?? account.external_account_id}
                </option>
              ))}
            </select>

            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Title (platforms that support it)"
              style={field}
            />
            <textarea
              value={text}
              onChange={(event) => setText(event.target.value)}
              rows={8}
              placeholder="Write content once; PAMASMMA routes it through the selected platform adapter."
              style={{ ...field, resize: "vertical" }}
            />
            <input
              value={mediaUrl}
              onChange={(event) => setMediaUrl(event.target.value)}
              placeholder="Public media URL (where required)"
              style={field}
            />
            <input
              type="datetime-local"
              value={scheduledAt}
              onChange={(event) => setScheduledAt(event.target.value)}
              style={field}
            />

            <button
              type="button"
              disabled={loading || !selectedAccount || !text.trim()}
              onClick={() => void publish()}
              style={{
                background: "#6B3FFB",
                color: "white",
                border: 0,
                borderRadius: 9,
                padding: "10px 15px",
                fontWeight: 700,
              }}
            >
              {loading ? "Working…" : scheduledAt ? "Queue Post" : "Publish Now"}
            </button>
          </div>
        )}

        {tab === "engagement" && (
          <div>
            {engagement.map((item) => (
              <div key={item.id} style={{ ...card, marginBottom: 9 }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: 10,
                    color: "#6A6A91",
                  }}
                >
                  <span>
                    {PLATFORM_LABELS[item.platform] ?? item.platform} ·{" "}
                    {item.author_name ?? "unknown"}
                  </span>
                  <span>
                    {item.priority.toUpperCase()} ·{" "}
                    {item.intent ?? "conversation"}
                  </span>
                </div>

                <div
                  style={{
                    fontSize: 12,
                    lineHeight: 1.6,
                    margin: "8px 0",
                  }}
                >
                  {item.text ?? "(no text)"}
                </div>

                <div style={{ display: "flex", gap: 7 }}>
                  <input
                    value={reply[item.id] ?? ""}
                    onChange={(event) =>
                      setReply((value) => ({
                        ...value,
                        [item.id]: event.target.value,
                      }))
                    }
                    placeholder="Reply…"
                    style={{ ...field, marginBottom: 0 }}
                  />
                  <button
                    type="button"
                    onClick={() => void sendReply(item)}
                    style={{
                      background: "#14152A",
                      color: "#BEB6FF",
                      border: "1px solid #29264B",
                      borderRadius: 8,
                      padding: "8px 12px",
                    }}
                  >
                    Send
                  </button>
                </div>
              </div>
            ))}

            {engagement.length === 0 && (
              <div style={{ padding: 18, color: "#5D5D80" }}>
                No synchronized engagement yet. Use Sync on a connected
                account.
              </div>
            )}
          </div>
        )}

        {tab === "analytics" && (
          <div style={{ ...card, maxWidth: 900 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: 12,
                alignItems: "center",
                marginBottom: 14,
              }}
            >
              <div>
                <div style={{ fontSize: 10, color: "#68688D" }}>
                  SELECTED ACCOUNT
                </div>
                <div style={{ fontSize: 14, marginTop: 4 }}>
                  {selected
                    ? PLATFORM_LABELS[selected.platform] ??
                      selected.platform
                    : "None"}
                </div>
              </div>
              <button
                type="button"
                onClick={() => void loadAnalytics()}
                disabled={analyticsLoading || !selectedAccount}
                style={{
                  background: "#12152A",
                  color: "#8DDCCF",
                  border: "1px solid #21443F",
                  borderRadius: 9,
                  padding: "9px 13px",
                }}
              >
                {analyticsLoading ? "Loading…" : "Load Analytics"}
              </button>
            </div>

            {analytics ? (
              <pre
                style={{
                  margin: 0,
                  whiteSpace: "pre-wrap",
                  overflowX: "auto",
                  background: "#070711",
                  borderRadius: 10,
                  border: "1px solid #1B1B31",
                  padding: 14,
                  color: "#A7A7C8",
                  fontSize: 11,
                  lineHeight: 1.5,
                }}
              >
                {JSON.stringify(analytics, null, 2)}
              </pre>
            ) : (
              <div style={{ color: "#5D5D80", fontSize: 12 }}>
                Load account analytics to inspect platform metrics. The exact
                metric set is provider-specific and capability-gated.
              </div>
            )}
          </div>
        )}

        {tab === "ads" && (
          <div style={{ ...card, maxWidth: 760 }}>
            <div
              style={{
                fontSize: 10,
                color: "#68688D",
                marginBottom: 12,
              }}
            >
              CAMPAIGN PLAN
            </div>

            <select
              value={selectedAccount}
              onChange={(event) => setSelectedAccount(event.target.value)}
              style={field}
            >
              <option value="">Select advertising account</option>
              {accounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {PLATFORM_LABELS[account.platform]} —{" "}
                  {account.display_name ?? account.external_account_id}
                </option>
              ))}
            </select>

            <input
              value={campaign.name}
              onChange={(event) =>
                setCampaign((value) => ({
                  ...value,
                  name: event.target.value,
                }))
              }
              placeholder="Campaign name"
              style={field}
            />
            <input
              value={campaign.adAccountId}
              onChange={(event) =>
                setCampaign((value) => ({
                  ...value,
                  adAccountId: event.target.value,
                }))
              }
              placeholder="Ad account ID"
              style={field}
            />
            <input
              value={campaign.objective}
              onChange={(event) =>
                setCampaign((value) => ({
                  ...value,
                  objective: event.target.value,
                }))
              }
              placeholder="Objective"
              style={field}
            />
            <input
              value={campaign.dailyBudget}
              onChange={(event) =>
                setCampaign((value) => ({
                  ...value,
                  dailyBudget: event.target.value,
                }))
              }
              placeholder="Daily budget"
              inputMode="decimal"
              style={field}
            />

            <div
              style={{
                display: "flex",
                gap: 8,
                flexWrap: "wrap",
              }}
            >
              <button
                type="button"
                onClick={() => void planAd()}
                style={{
                  background: "#D4AF37",
                  color: "#08080F",
                  border: 0,
                  borderRadius: 9,
                  padding: "10px 15px",
                  fontWeight: 800,
                }}
              >
                Plan Campaign
              </button>

              {plannedCampaignId && (
                <button
                  type="button"
                  onClick={() => void approveAd()}
                  style={{
                    background: "#55D6BE",
                    color: "#07120F",
                    border: 0,
                    borderRadius: 9,
                    padding: "10px 15px",
                    fontWeight: 800,
                  }}
                >
                  Approve &amp; Execute
                </button>
              )}
            </div>

            <div
              style={{
                marginTop: 14,
                padding: 12,
                borderRadius: 9,
                background: "#0D0E17",
                border: "1px solid #27263A",
                color: "#777796",
                fontSize: 10,
                lineHeight: 1.6,
              }}
            >
              PAMASMMA can prepare and submit a campaign only after explicit
              approval. Autonomous advertising spend remains disabled by
              default.
            </div>
          </div>
        )}
      </section>
    </main>
  );
}
