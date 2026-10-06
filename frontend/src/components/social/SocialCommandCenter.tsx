"use client";

import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { social } from "@/lib/api";

type Account={id:string;platform:string;external_account_id:string;display_name?:string|null;status:string;capabilities:string[]};
type PlatformInfo={platform:string;capabilities:string[]};
type Engagement={id:string;account_id:string;platform:string;item_id:string;text?:string|null;intent?:string|null;sentiment?:string|null;priority:string;author_name?:string|null};

const PLATFORM_LABELS:Record<string,string>={facebook:"Facebook",instagram:"Instagram",tiktok:"TikTok",youtube:"YouTube",linkedin:"LinkedIn",x:"X",threads:"Threads",pinterest:"Pinterest",reddit:"Reddit",telegram:"Telegram",whatsapp:"WhatsApp"};

export function SocialCommandCenter(){
  const [platforms,setPlatforms]=useState<PlatformInfo[]>([]); const [accounts,setAccounts]=useState<Account[]>([]); const [engagement,setEngagement]=useState<Engagement[]>([]);
  const [selectedAccount,setSelectedAccount]=useState(""); const [text,setText]=useState(""); const [mediaUrl,setMediaUrl]=useState(""); const [title,setTitle]=useState(""); const [scheduledAt,setScheduledAt]=useState("");
  const [reply,setReply]=useState<Record<string,string>>({}); const [loading,setLoading]=useState(false); const [tab,setTab]=useState<"accounts"|"publish"|"engagement"|"ads">("accounts");
  const [campaign,setCampaign]=useState({name:"",objective:"OUTCOME_TRAFFIC",daily_budget:"",currency:"USD",ad_account_id:""});

  const refresh=async()=>{const [p,a,e]=await Promise.all([social.platforms(),social.accounts(),social.engagement()]);setPlatforms(p.platforms);setAccounts(a.accounts);setEngagement(e.items);if(!selectedAccount&&a.accounts[0])setSelectedAccount(a.accounts[0].id);};
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const [p, a, e] = await Promise.all([
          social.platforms(),
          social.accounts(),
          social.engagement(),
        ]);
        if (cancelled) return;
        setPlatforms(p.platforms);
        setAccounts(a.accounts);
        setEngagement(e.items);
        if (a.accounts[0]) {
          setSelectedAccount(a.accounts[0].id);
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

  const connect=async(platform:string)=>{try{const r=await social.oauthStart(platform);window.location.assign(r.authorization_url);}catch(e){toast.error(e instanceof Error?e.message:"OAuth is not configured");}};
  const publish=async()=>{if(!selectedAccount||!text.trim()){toast.error("Select an account and enter content");return;}setLoading(true);try{await social.publish({command:{account_id:selectedAccount,text:text.trim(),...(mediaUrl?{media_url:mediaUrl}:{}),...(title?{title}: {})},...(scheduledAt?{scheduled_at:new Date(scheduledAt).toISOString()}: {})});toast.success(scheduledAt?"Post queued":"Published");setText("");setMediaUrl("");setTitle("");setScheduledAt("");}catch(e){toast.error(e instanceof Error?e.message:"Publishing failed");}finally{setLoading(false);}};
  const sync=async(accountId:string)=>{try{const r=await social.sync(accountId);toast.success(`${r.count} engagement items synchronized`);await refresh();}catch(e){toast.error(e instanceof Error?e.message:"Sync failed");}};
  const sendReply=async(item:Engagement)=>{const body=reply[item.id]?.trim();if(!body)return;try{await social.reply({account_id:item.account_id,item_id:item.item_id,text:body});toast.success("Reply sent");setReply(v=>({...v,[item.id]:""}));}catch(e){toast.error(e instanceof Error?e.message:"Reply failed");}};
  const planAd=async()=>{if(!selectedAccount||!campaign.name.trim()){toast.error("Select an account and name the campaign");return;}try{const r=await social.planCampaign({account_id:selectedAccount,ad_account_id:campaign.ad_account_id||undefined,name:campaign.name,objective:campaign.objective,daily_budget:campaign.daily_budget?Number(campaign.daily_budget):undefined,currency:campaign.currency});toast.success(`Campaign planned: ${r.campaign_id}`);}catch(e){toast.error(e instanceof Error?e.message:"Campaign planning failed");}};

  return <main style={{minHeight:"100vh",background:"#04040D",color:"#DDE0F0",padding:24,fontFamily:"Inter,system-ui,sans-serif"}}>
    <header style={{maxWidth:1180,margin:"0 auto 24px",display:"flex",justifyContent:"space-between",gap:16,alignItems:"center"}}><div><div style={{fontSize:10,letterSpacing:3,color:"#6B3FFB"}}>PAMASMMA / SOCIAL GROWTH</div><h1 style={{fontSize:28,margin:"6px 0"}}>Social Command Center</h1><div style={{color:"#66668C",fontSize:12}}>Connect, publish, listen, respond, measure and govern campaigns from one control plane.</div></div><div style={{fontSize:10,color:"#55D6BE",border:"1px solid #1D5048",borderRadius:99,padding:"7px 11px"}}>ADS REQUIRE APPROVAL</div></header>
    <nav style={{maxWidth:1180,margin:"0 auto 18px",display:"flex",gap:8,flexWrap:"wrap"}}>{(["accounts","publish","engagement","ads"] as const).map(x=><button key={x} onClick={()=>setTab(x)} style={{background:tab===x?"#181432":"#0A0A18",color:tab===x?"#E8E8FA":"#66668C",border:"1px solid #1A1A32",borderRadius:9,padding:"9px 13px",fontSize:11,textTransform:"uppercase"}}>{x}</button>)}</nav>
    <section style={{maxWidth:1180,margin:"0 auto"}}>
      {tab==="accounts"&&<div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(210px,1fr))",gap:10}}>{platforms.map(p=><div key={p.platform} style={{background:"#0A0A18",border:"1px solid #1A1A32",borderRadius:12,padding:15}}><div style={{fontWeight:700}}>{PLATFORM_LABELS[p.platform]??p.platform}</div><div style={{color:"#55557C",fontSize:10,margin:"7px 0 12px",lineHeight:1.5}}>{p.capabilities.join(" · ")}</div><button onClick={()=>connect(p.platform)} style={{width:"100%",background:"#12112B",border:"1px solid #29234D",color:"#B6A6FF",padding:"8px 10px",borderRadius:8}}>Connect</button></div>)}<div style={{gridColumn:"1/-1",marginTop:10}}>{accounts.length===0?<div style={{padding:18,border:"1px dashed #242444",borderRadius:12,color:"#59597D",fontSize:12}}>No social accounts connected yet.</div>:accounts.map(a=><div key={a.id} style={{display:"flex",justifyContent:"space-between",alignItems:"center",gap:12,padding:12,marginBottom:7,background:"#0A0A18",border:"1px solid #1A1A32",borderRadius:10}}><div><b>{PLATFORM_LABELS[a.platform]??a.platform}</b><div style={{fontSize:10,color:"#5C5C82"}}>{a.display_name??a.external_account_id} · {a.status}</div></div><div style={{display:"flex",gap:8}}><button onClick={()=>setSelectedAccount(a.id)} style={{padding:"7px 9px",background:selectedAccount===a.id?"#241D42":"#12121F",color:"#DDE0F0",border:"1px solid #2B2850",borderRadius:7,fontSize:10}}>Use</button><button onClick={()=>void sync(a.id)} style={{padding:"7px 9px",background:"#101A19",color:"#78DCCB",border:"1px solid #21443F",borderRadius:7,fontSize:10}}>Sync</button></div></div>)}</div></div>}
      {tab==="publish"&&<div style={{maxWidth:760,background:"#0A0A18",border:"1px solid #1A1A32",borderRadius:14,padding:18}}><div style={{fontSize:10,color:"#68688D",marginBottom:8}}>ACCOUNT</div><select value={selectedAccount} onChange={e=>setSelectedAccount(e.target.value)} style={{width:"100%",background:"#070711",color:"#DDDDF0",padding:11,borderRadius:8,border:"1px solid #26263F",marginBottom:12}}><option value="">Select account</option>{accounts.map(a=><option key={a.id} value={a.id}>{PLATFORM_LABELS[a.platform]} — {a.display_name??a.external_account_id}</option>)}</select><input value={title} onChange={e=>setTitle(e.target.value)} placeholder="Title (platforms that support it)" style={field}/><textarea value={text} onChange={e=>setText(e.target.value)} rows={8} placeholder="Write content once; PAMASMMA routes it through the selected platform adapter." style={{...field,resize:"vertical"}}/><input value={mediaUrl} onChange={e=>setMediaUrl(e.target.value)} placeholder="Public media URL (where required)" style={field}/><input type="datetime-local" value={scheduledAt} onChange={e=>setScheduledAt(e.target.value)} style={field}/><button disabled={loading||!selectedAccount||!text.trim()} onClick={()=>void publish()} style={{background:"#6B3FFB",color:"white",border:0,borderRadius:9,padding:"10px 15px",fontWeight:700}}>{loading?"Working…":scheduledAt?"Queue Post":"Publish Now"}</button></div>}
      {tab==="engagement"&&<div>{engagement.map(i=><div key={i.id} style={{background:"#0A0A18",border:"1px solid #1A1A32",borderRadius:12,padding:14,marginBottom:9}}><div style={{display:"flex",justifyContent:"space-between",fontSize:10,color:"#6A6A91"}}><span>{PLATFORM_LABELS[i.platform]??i.platform} · {i.author_name??"unknown"}</span><span>{i.priority.toUpperCase()} · {i.intent??"conversation"}</span></div><div style={{fontSize:12,lineHeight:1.6,margin:"8px 0"}}>{i.text??"(no text)"}</div><div style={{display:"flex",gap:7}}><input value={reply[i.id]??""} onChange={e=>setReply(v=>({...v,[i.id]:e.target.value}))} placeholder="Reply…" style={{...field,marginBottom:0}}/><button onClick={()=>void sendReply(i)} style={{background:"#14152A",color:"#BEB6FF",border:"1px solid #29264B",borderRadius:8,padding:"8px 12px"}}>Send</button></div></div>)}{engagement.length===0&&<div style={{padding:18,color:"#5D5D80"}}>No synchronized engagement yet. Use Sync on a connected account.</div>}</div>}
      {tab==="ads"&&<div style={{maxWidth:760,background:"#0A0A18",border:"1px solid #1A1A32",borderRadius:14,padding:18}}><div style={{fontSize:10,color:"#68688D",marginBottom:12}}>CAMPAIGN PLAN</div><input value={campaign.name} onChange={e=>setCampaign({...campaign,name:e.target.value})} placeholder="Campaign name" style={field}/><input value={campaign.ad_account_id} onChange={e=>setCampaign({...campaign,ad_account_id:e.target.value})} placeholder="Ad account ID" style={field}/><input value={campaign.objective} onChange={e=>setCampaign({...campaign,objective:e.target.value})} placeholder="Objective" style={field}/><input value={campaign.daily_budget} onChange={e=>setCampaign({...campaign,daily_budget:e.target.value})} placeholder="Daily budget" inputMode="decimal" style={field}/><button onClick={()=>void planAd()} style={{background:"#D4AF37",color:"#08080F",border:0,borderRadius:9,padding:"10px 15px",fontWeight:800}}>Plan Campaign (Approval Required)</button></div>}
    </section>
  </main>;
}

const field:React.CSSProperties={width:"100%",boxSizing:"border-box",background:"#070711",color:"#DDDDF0",padding:"11px",borderRadius:8,border:"1px solid #26263F",marginBottom:10,fontSize:12};
