"use client";

import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";

import { jarvis } from "@/lib/api";
import type { JarvisConversation, JarvisMessage } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";

type TranscriptSegment = { endMs: number; text: string };

function nextJarvisEventId(sequence: { current: number }, prefix: string): string {
  sequence.current += 1;
  return `jarvis-${prefix}-${sequence.current}`;
}

async function waitForIceGathering(peer: RTCPeerConnection, timeoutMs = 15000): Promise<void> {
  if (peer.iceGatheringState === "complete") return;
  await new Promise<void>((resolve, reject) => {
    const timeout = window.setTimeout(() => {
      peer.removeEventListener("icegatheringstatechange", onChange);
      reject(new Error("Timed out preparing the secure voice connection."));
    }, timeoutMs);
    const onChange = () => {
      if (peer.iceGatheringState === "complete") {
        window.clearTimeout(timeout);
        peer.removeEventListener("icegatheringstatechange", onChange);
        resolve();
      }
    };
    peer.addEventListener("icegatheringstatechange", onChange);
  });
}

export default function JarvisPage() {
  const router = useRouter();
  const { isAuthenticated, isRestoring, logout } = useAuth();
  const [conversations, setConversations] = useState<JarvisConversation[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [messages, setMessages] = useState<JarvisMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [voiceStarting, setVoiceStarting] = useState(false);
  const [voiceConnected, setVoiceConnected] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState("Voice off");
  const [cognition, setCognition] = useState<{provider?:string;confidence?:number;evidence_status?:string}|null>(null);

  const peerRef = useRef<RTCPeerConnection | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const channelRef = useRef<RTCDataChannel | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const transcriptSegmentsRef = useRef<TranscriptSegment[]>([]);
  const handledDelegationsRef = useRef<Set<string>>(new Set());
  const closeTimeoutRef = useRef<number | null>(null);
  const eventSequenceRef = useRef(0);
  const voiceSessionIdRef = useRef<string | null>(null);
  const voiceConversationIdRef = useRef<string | null>(null);

  const notifyVoiceSessionClosed = () => {
    const sessionId = voiceSessionIdRef.current;
    const conversationId = voiceConversationIdRef.current;
    voiceSessionIdRef.current = null;
    voiceConversationIdRef.current = null;
    if (sessionId && conversationId) {
      void jarvis.closeVoiceSession(conversationId, sessionId).catch(() => {
        setVoiceStatus("Voice ended; server session will expire automatically");
      });
    }
  };

  const cleanupVoice = () => {
    notifyVoiceSessionClosed();
    if (closeTimeoutRef.current !== null) {
      window.clearTimeout(closeTimeoutRef.current);
      closeTimeoutRef.current = null;
    }
    channelRef.current?.close();
    peerRef.current?.close();
    streamRef.current?.getTracks().forEach((track) => track.stop());
    if (audioRef.current) audioRef.current.srcObject = null;
    channelRef.current = null;
    peerRef.current = null;
    streamRef.current = null;
    audioRef.current = null;
    transcriptSegmentsRef.current = [];
    setVoiceConnected(false);
    setVoiceStarting(false);
    setVoiceStatus("Voice off");
  };

  const stopVoice = () => {
    const channel = channelRef.current;
    if (channel?.readyState === "open") {
      setVoiceStatus("Closing voice session…");
      channel.send(JSON.stringify({
        type: "session.close",
        event_id: nextJarvisEventId(eventSequenceRef, "close"),
      }));
      closeTimeoutRef.current = window.setTimeout(cleanupVoice, 5000);
    } else {
      cleanupVoice();
    }
  };

  useEffect(() => {
    if (isRestoring) return;
    if (!isAuthenticated) {
      router.replace("/auth");
      return;
    }

    let active = true;
    void (async () => {
      setLoading(true);
      try {
        const result = await jarvis.listConversations();
        if (active) setConversations(result.conversations);
      } catch (error) {
        if (active) toast.error(error instanceof Error ? error.message : "Could not load JARVIS conversations.");
      } finally {
        if (active) setLoading(false);
      }
    })();

    return () => {
      active = false;
    };
  }, [isAuthenticated, isRestoring, router]);

  useEffect(() => () => {
    const channel = channelRef.current;
    if (channel?.readyState === "open") {
      channel.send(JSON.stringify({ type: "session.close", event_id: nextJarvisEventId(eventSequenceRef, "unmount") }));
    }
    notifyVoiceSessionClosed();
    channel?.close();
    peerRef.current?.close();
    streamRef.current?.getTracks().forEach((track) => track.stop());
  }, []);

  const selected = conversations.find((item) => item.id === selectedId) ?? null;

  const openConversation = async (conversationId: string) => {
    if (sending) return;
    if (voiceConnected || voiceStarting) stopVoice();
    setSelectedId(conversationId);
    setMessages([]);
    setCognition(null);
    setLoading(true);
    try {
      const result = await jarvis.getConversation(conversationId);
      setMessages(result.messages);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not open conversation.");
    } finally {
      setLoading(false);
    }
  };

  const newConversation = async () => {
    if (sending) return;
    if (voiceConnected || voiceStarting) stopVoice();
    try {
      const result = await jarvis.createConversation();
      setConversations((previous) => [result.conversation, ...previous]);
      setSelectedId(result.conversation.id);
      setMessages([]);
      setCognition(null);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not create a conversation.");
    }
  };

  const sendDelegatedTurn = async (
    conversationId: string,
    delegationId: string,
    transcript: string,
    channel: RTCDataChannel,
  ) => {
    try {
      const result = await jarvis.completeVoiceDelegation(conversationId, delegationId, transcript);
      setMessages((previous) => [...previous, result.turn.user_message, result.turn.assistant_message]);
      setCognition({
        provider: result.turn.cognition.provider,
        confidence: result.turn.cognition.confidence,
        evidence_status: result.turn.cognition.evidence_status,
      });
      const now = new Date().toISOString();
      setConversations((previous) =>
        previous.map((item) =>
          item.id === conversationId
            ? {
                ...item,
                title: item.title === "New conversation" ? transcript.slice(0, 80) : item.title,
                last_message_at: now,
                updated_at: now,
              }
            : item,
        ),
      );
      if (channel.readyState === "open") {
        channel.send(JSON.stringify({
          type: "session.commentary.append",
          event_id: nextJarvisEventId(eventSequenceRef, "result"),
          delegation_id: delegationId,
          content: result.spoken_response.slice(0, 1400),
        }));
      }
      setVoiceStatus("Listening");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "JARVIS could not process the voice request.");
      if (channel.readyState === "open") {
        channel.send(JSON.stringify({
          type: "session.commentary.append",
          event_id: nextJarvisEventId(eventSequenceRef, "error"),
          delegation_id: delegationId,
          content: "I could not reach PAMASMMA's reasoning service just now. Please repeat your request.",
        }));
      }
      setVoiceStatus("Listening");
    }
  };

  const startVoice = async () => {
    if (voiceStarting || voiceConnected || sending) return;
    setVoiceStarting(true);
    setVoiceStatus("Requesting microphone permission…");
    let conversationId = selectedId;

    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error("Microphone access requires a supported browser and a secure HTTPS connection.");
      }
      if (!conversationId) {
        const created = await jarvis.createConversation();
        conversationId = created.conversation.id;
        setSelectedId(conversationId);
        setConversations((previous) => [created.conversation, ...previous]);
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      streamRef.current = stream;

      const peer = new RTCPeerConnection();
      peerRef.current = peer;
      const remoteAudio = new Audio();
      remoteAudio.autoplay = true;
      audioRef.current = remoteAudio;
      peer.ontrack = (event) => {
        if (event.streams[0]) {
          remoteAudio.srcObject = event.streams[0];
          void remoteAudio.play().catch(() => {
            setVoiceStatus("Tap the page once to enable speaker playback.");
          });
        }
      };
      stream.getTracks().forEach((track) => peer.addTrack(track, stream));

      const dataChannel = peer.createDataChannel("oai-events");
      channelRef.current = dataChannel;
      transcriptSegmentsRef.current = [];
      handledDelegationsRef.current = new Set();

      dataChannel.onopen = () => {
        setVoiceConnected(true);
        setVoiceStarting(false);
        setVoiceStatus("Listening · microphone active");
      };
      dataChannel.onclose = () => {
        cleanupVoice();
      };
      dataChannel.onerror = () => {
        setVoiceStatus("Voice data channel error");
        cleanupVoice();
      };
      dataChannel.onmessage = (messageEvent) => {
        let event: Record<string, unknown>;
        try {
          event = JSON.parse(String(messageEvent.data)) as Record<string, unknown>;
        } catch {
          return;
        }

        if (event.type === "session.input_transcript.delta" && typeof event.delta === "string") {
          transcriptSegmentsRef.current.push({
            endMs: typeof event.end_ms === "number" ? event.end_ms : Number.POSITIVE_INFINITY,
            text: event.delta,
          });
          return;
        }

        if (event.type === "session.delegation.created") {
          const delegation = event.delegation as { id?: string; target?: string } | undefined;
          const delegationId = delegation?.id;
          if (!delegationId || delegation.target !== "client" || handledDelegationsRef.current.has(delegationId)) return;
          handledDelegationsRef.current.add(delegationId);

          const offsetMs = typeof event.offset_ms === "number" ? event.offset_ms : Number.POSITIVE_INFINITY;
          const eligible = transcriptSegmentsRef.current.filter((segment) => !Number.isFinite(segment.endMs) || segment.endMs <= offsetMs);
          const transcript = eligible.map((segment) => segment.text).join("").trim();
          transcriptSegmentsRef.current = transcriptSegmentsRef.current.filter((segment) => segment.endMs > offsetMs);

          if (!transcript) {
            if (dataChannel.readyState === "open") {
              dataChannel.send(JSON.stringify({
                type: "session.commentary.append",
                event_id: `jarvis-empty-${Date.now()}`,
                delegation_id: delegationId,
                content: "I did not receive a clear transcript. Please say that again.",
              }));
            }
            return;
          }

          setVoiceStatus("Working · " + transcript.slice(0, 44));
          dataChannel.send(JSON.stringify({
            type: "session.commentary.append",
            event_id: `jarvis-progress-${Date.now()}`,
            delegation_id: delegationId,
            content: "I’m checking that now.",
          }));
          void sendDelegatedTurn(conversationId as string, delegationId, transcript, dataChannel);
          return;
        }

        if (event.type === "session.closed") {
          cleanupVoice();
          return;
        }

        if (event.type === "error") {
          const detail = event.error as { message?: string } | undefined;
          setVoiceStatus(detail?.message ?? "Voice session reported an error");
        }
      };

      peer.onconnectionstatechange = () => {
        if (peer.connectionState === "failed" || peer.connectionState === "closed") {
          setVoiceStatus("Voice connection lost");
          cleanupVoice();
        }
      };

      setVoiceStatus("Negotiating secure audio…");
      const offer = await peer.createOffer();
      await peer.setLocalDescription(offer);
      await waitForIceGathering(peer);
      const localSdp = peer.localDescription?.sdp;
      if (!localSdp) throw new Error("Could not create the WebRTC offer.");

      const liveSession = await jarvis.createVoiceSession(conversationId, localSdp);
      voiceSessionIdRef.current = liveSession.session_id;
      voiceConversationIdRef.current = conversationId;
      await peer.setRemoteDescription({ type: "answer", sdp: liveSession.sdp });
      setVoiceStatus("Connecting to JARVIS voice…");
    } catch (error) {
      cleanupVoice();
      toast.error(error instanceof Error ? error.message : "Could not start JARVIS voice.");
    } finally {
      setVoiceStarting(false);
    }
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const content = draft.trim();
    if (!content || sending || voiceConnected || voiceStarting) return;

    setSending(true);
    setDraft("");
    let conversationId = selectedId;
    try {
      if (!conversationId) {
        const created = await jarvis.createConversation();
        conversationId = created.conversation.id;
        setSelectedId(conversationId);
        setConversations((previous) => [created.conversation, ...previous]);
      }

      const optimisticId = `local-${Date.now()}`;
      const optimistic: JarvisMessage = {
        id: optimisticId,
        sequence: messages.length + 1,
        role: "user",
        content,
        modality: "text",
        created_at: new Date().toISOString(),
      };
      setMessages((previous) => [...previous, optimistic]);

      const result = await jarvis.sendTurn(conversationId, content);
      setMessages((previous) => [
        ...previous.filter((message) => message.id !== optimisticId),
        result.user_message,
        result.assistant_message,
      ]);
      setCognition({
        provider: result.cognition.provider,
        confidence: result.cognition.confidence,
        evidence_status: result.cognition.evidence_status,
      });
      const now = new Date().toISOString();
      setConversations((previous) =>
        previous.map((item) =>
          item.id === conversationId
            ? {
                ...item,
                title: item.title === "New conversation" ? content.slice(0, 80) : item.title,
                last_message_at: now,
                updated_at: now,
              }
            : item,
        ),
      );
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "JARVIS could not complete the turn.");
      if (conversationId) {
        try {
          const refreshed = await jarvis.getConversation(conversationId);
          if (selectedId === conversationId) setMessages(refreshed.messages);
        } catch {
          // Preserve the original error; the next conversation refresh can recover.
        }
      }
    } finally {
      setSending(false);
    }
  };

  if (isRestoring || !isAuthenticated) {
    return (
      <main className="grid min-h-screen place-items-center bg-[#04040D] text-[#77779A]">
        <p className="font-mono text-xs tracking-[0.2em]">RESTORING SECURE SESSION…</p>
      </main>
    );
  }

  return (
    <main className="flex h-screen overflow-hidden bg-[#04040D] text-[#D0D0EC]">
      <aside className="flex w-[290px] shrink-0 flex-col border-r border-[#1A1A3A] bg-[#07071A] max-md:w-[108px]">
        <div className="border-b border-[#1A1A3A] px-5 py-6 max-md:px-3">
          <div className="font-mono text-[10px] tracking-[0.28em] text-[#D4AF37]">PAMASMMA</div>
          <h1 className="mt-2 text-xl font-semibold tracking-[0.12em] text-[#F0F0F8] max-md:text-sm">JARVIS</h1>
          <p className="mt-1 text-[10px] text-[#6F6F99] max-md:hidden">Executive companion</p>
        </div>
        <div className="p-3">
          <button
            type="button"
            onClick={() => void newConversation()}
            disabled={sending || voiceConnected || voiceStarting}
            className="w-full rounded-lg border border-[#66502A] bg-[#211B12] px-3 py-3 text-left text-xs font-semibold tracking-wide text-[#E7C56B] transition hover:bg-[#302515] disabled:opacity-40"
          >
            <span className="max-md:hidden">＋ NEW CONVERSATION</span>
            <span className="hidden max-md:inline">＋ NEW</span>
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-3">
          <p className="px-3 py-2 font-mono text-[9px] tracking-[0.18em] text-[#55557C] max-md:hidden">RECENT CONVERSATIONS</p>
          {loading && conversations.length === 0 ? (
            <p className="px-3 py-3 text-xs text-[#66668D]">Loading…</p>
          ) : conversations.length === 0 ? (
            <p className="px-3 py-3 text-xs leading-5 text-[#66668D] max-md:hidden">Your conversations will appear here.</p>
          ) : conversations.map((conversation) => (
            <button
              key={conversation.id}
              type="button"
              onClick={() => void openConversation(conversation.id)}
              disabled={sending || voiceConnected || voiceStarting}
              aria-current={selectedId === conversation.id ? "page" : undefined}
              title={conversation.title}
              className={`mb-1 w-full rounded-lg px-3 py-3 text-left text-xs transition disabled:opacity-50 ${selectedId === conversation.id ? "border border-[#57452A] bg-[#19150F] text-[#E9D49B]" : "border border-transparent text-[#9696B8] hover:bg-[#101027]"}`}
            >
              <span className="block truncate">{conversation.title}</span>
              <span className="mt-1 block font-mono text-[9px] text-[#55557C] max-md:hidden">
                {conversation.last_message_at ? new Date(conversation.last_message_at).toLocaleString() : "NEW"}
              </span>
            </button>
          ))}
        </div>
        <div className="border-t border-[#1A1A3A] p-3">
          <button type="button" onClick={() => router.push("/dashboard")} className="mb-2 w-full rounded-lg px-3 py-2 text-left text-xs text-[#8888AD] hover:bg-[#111130]">← PAMASMMA</button>
          <button type="button" onClick={() => void logout()} className="w-full px-3 py-2 text-left font-mono text-[9px] tracking-widest text-[#55557C] hover:text-[#D0D0EC]">LOG OUT</button>
        </div>
      </aside>

      <section className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-[#1A1A3A] bg-[#07071A] px-6 py-4 max-sm:px-4">
          <div>
            <p className="font-mono text-[9px] tracking-[0.2em] text-[#77779A]">PERSONAL AI COMPANION</p>
            <h2 className="mt-1 text-sm font-semibold text-[#ECECF8]">{selected?.title ?? "JARVIS interface"}</h2>
          </div>
          <div className="text-right">
            <p className="font-mono text-[9px] tracking-widest text-[#71CDA2]">CORE ONLINE</p>
            <p className="mt-1 text-[9px] text-[#66668D]">{voiceConnected ? voiceStatus.toUpperCase() : "TEXT MODE · VOICE REQUIRES BACKEND API KEY"}</p>
          </div>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-6 max-sm:px-3">
          {messages.length === 0 && !loading ? (
            <div className="mx-auto mt-20 max-w-xl text-center">
              <div className="mx-auto grid h-20 w-20 place-items-center rounded-full border border-[#78613A] bg-[#19150F] text-3xl text-[#D4AF37] shadow-[0_0_60px_rgba(212,175,55,0.12)]">⬡</div>
              <p className="mt-6 font-mono text-[10px] tracking-[0.3em] text-[#D4AF37]">JARVIS · PAMASMMA</p>
              <h3 className="mt-3 text-2xl font-light text-[#F0F0F8]">At your service.</h3>
              <p className="mx-auto mt-3 max-w-md text-sm leading-7 text-[#8585A8]">I can help you reason, plan, analyze and coordinate your PAMASMMA work. Speak naturally or type; substantive voice requests are delegated to PAMASMMA&apos;s CognitiveEngine.</p>
            </div>
          ) : (
            <div className="mx-auto flex max-w-4xl flex-col gap-5">
              {messages.map((message) => (
                <div key={message.id} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-[88%] rounded-2xl px-4 py-3 text-sm leading-7 whitespace-pre-wrap ${message.role === "user" ? "rounded-br-sm bg-[#292044] text-[#F0EAFE]" : "rounded-bl-sm border border-[#29243A] bg-[#0B0B20] text-[#D0D0EC]"}`}>
                    {message.content}
                    {message.modality === "voice" && <span className="ml-2 font-mono text-[8px] text-[#77779A]">VOICE</span>}
                  </div>
                </div>
              ))}
              {sending && (
                <div className="flex items-center gap-2 text-xs text-[#8585A8]">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-[#D4AF37]" />
                  JARVIS is thinking…
                </div>
              )}
            </div>
          )}
        </div>

        {cognition && (
          <div className="border-t border-[#17172F] bg-[#07071A] px-6 py-2 font-mono text-[9px] text-[#66668D]">
            PROVIDER {cognition.provider ?? "—"} · CONFIDENCE {typeof cognition.confidence === "number" ? Math.round(cognition.confidence * 100) + "%" : "—"} · EVIDENCE {cognition.evidence_status ?? "—"}
          </div>
        )}

        <form onSubmit={submit} className="border-t border-[#1A1A3A] bg-[#07071A] p-4 sm:p-5">
          <div className="mx-auto flex max-w-4xl items-end gap-3">
            <textarea
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  event.currentTarget.form?.requestSubmit();
                }
              }}
              rows={2}
              maxLength={12000}
              placeholder={voiceConnected ? "Voice conversation active…" : "Talk to JARVIS about PAMASMMA…"}
              aria-label="Message JARVIS"
              disabled={sending || voiceConnected || voiceStarting}
              className="min-h-[54px] flex-1 resize-y rounded-xl border border-[#292943] bg-[#0C0C22] px-4 py-3 text-sm leading-6 text-[#E0E0F0] outline-none placeholder:text-[#55557C] focus:border-[#8C7040] disabled:opacity-50"
            />
            <button
              type="button"
              onClick={() => voiceConnected ? stopVoice() : void startVoice()}
              disabled={voiceStarting || sending}
              title={voiceConnected ? "Close voice session" : "Start a voice conversation"}
              aria-label={voiceConnected ? "Stop voice conversation" : "Start voice conversation"}
              className={`grid h-[54px] min-w-[72px] shrink-0 place-items-center rounded-xl border px-3 text-[10px] font-semibold tracking-wider transition disabled:opacity-40 ${voiceConnected ? "border-[#8D3C45] bg-[#32161B] text-[#F0B6BE]" : "border-[#66502A] bg-[#211B12] text-[#E7C56B] hover:bg-[#302515]"}`}
            >
              {voiceStarting ? "…" : voiceConnected ? "STOP" : "MIC"}
            </button>
            <button
              type="submit"
              disabled={sending || !draft.trim() || voiceConnected || voiceStarting}
              className="h-[54px] rounded-xl border border-[#78613A] bg-[#302515] px-5 text-xs font-semibold tracking-wider text-[#E9D49B] transition hover:bg-[#40321C] disabled:cursor-not-allowed disabled:opacity-40"
            >
              {sending ? "…" : "SEND"}
            </button>
          </div>
          <p className="mx-auto mt-2 max-w-4xl font-mono text-[8px] tracking-wider text-[#4F4F73]">{voiceConnected ? voiceStatus.toUpperCase() : "ENTER TO SEND · SHIFT + ENTER FOR NEW LINE · CONVERSATIONS SAVED TO PAMASMMA"}</p>
        </form>
      </section>
    </main>
  );
}
