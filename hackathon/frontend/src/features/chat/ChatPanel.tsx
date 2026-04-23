import { useRef, useEffect } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import IconButton from "@mui/material/IconButton";
import Chip from "@mui/material/Chip";
import Card from "@mui/material/Card";
import CircularProgress from "@mui/material/CircularProgress";
import SendIcon from "@mui/icons-material/Send";
import { useAppSelector, useAppDispatch } from "../../app/hooks";
import { addMessage, setInputDraft, setLoading } from "./chatSlice";
import { useSendChatMessageMutation } from "../../services/chatApi";
import ChatBubble from "./ChatBubble";
import type { ChatMessageIn } from "../../services/types";

const QUICK_CHIPS = [
  { label: "Who should I assign?", draft: "Who should I assign to each station for the Morning shift?" },
  { label: "Fill empty slots", draft: "Suggest assignments for all empty station slots based on crew skills and availability" },
  { label: "Why this rec?", draft: "Why did the AI recommend this many staff for each station?" },
  { label: "What if rain?", draft: "What if it rains today? How should I adjust staffing?" },
];

const MAX_HISTORY = 10;

export default function ChatPanel() {
  const dispatch = useAppDispatch();
  const { messages, inputDraft, loading } = useAppSelector((s) => s.chat);
  const storeId = useAppSelector((s) => s.storeProfile.selectedStoreId);
  const staffing = useAppSelector((s) => s.suggestion.staffing);
  const cells = useAppSelector((s) => s.deployment.cells);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [sendChat] = useSendChatMessageMutation();

  useEffect(() => {
    if (messages.length === 0) {
      dispatch(
        addMessage({
          id: "sys-1",
          role: "system",
          content: "AI Assistant connected — ask questions about staffing or request assignment suggestions.",
          timestamp: new Date().toISOString(),
        })
      );
      dispatch(
        addMessage({
          id: "ai-1",
          role: "ai",
          content:
            "I can help you assign crew to stations based on skills, availability, and past performance. Ask me anything or try one of the quick actions below.",
          timestamp: new Date().toISOString(),
        })
      );
    }
  }, [messages.length, dispatch]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages.length, loading]);

  const handleSend = async () => {
    const text = inputDraft.trim();
    if (!text || loading) return;

    dispatch(
      addMessage({
        id: `user-${Date.now()}`,
        role: "user",
        content: text,
        timestamp: new Date().toISOString(),
      })
    );
    dispatch(setInputDraft(""));
    dispatch(setLoading(true));

    const history: ChatMessageIn[] = messages
      .filter((m) => m.role !== "system")
      .slice(-MAX_HISTORY)
      .map((m) => ({ role: m.role, content: m.content }));

    try {
      const result = await sendChat({
        message: text,
        conversation_history: history,
        store_id: storeId ?? "",
        date: staffing?.date ?? new Date().toISOString().slice(0, 10),
        current_cells: cells,
      }).unwrap();

      dispatch(
        addMessage({
          id: `ai-${Date.now()}`,
          role: "ai",
          content: result.message,
          timestamp: new Date().toISOString(),
          actions: result.actions,
        })
      );
    } catch {
      dispatch(
        addMessage({
          id: `ai-err-${Date.now()}`,
          role: "ai",
          content: "Sorry, I couldn't get a response. Make sure Ollama is running (`ollama serve`) and a model is pulled.",
          timestamp: new Date().toISOString(),
        })
      );
    } finally {
      dispatch(setLoading(false));
    }
  };

  return (
    <Card
      sx={{
        display: "flex",
        flexDirection: "column",
        height: 520,
        overflow: "hidden",
        p: 0,
      }}
    >
      <Box
        sx={(t) => ({
          px: 2,
          py: 1.5,
          borderBottom: 1,
          borderColor: "divider",
          bgcolor: t.palette.mode === "dark" ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.02)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderRadius: "28px 28px 0 0",
        })}
      >
        <Typography variant="body2" sx={{ fontWeight: 700, display: "flex", alignItems: "center", gap: 0.75 }}>
          <Box component="span" sx={{ color: "primary.main" }}>◆</Box> AI Assistant
        </Typography>
        {loading && <CircularProgress size={14} color="primary" />}
      </Box>

      <Box
        ref={scrollRef}
        sx={{
          flex: 1,
          overflowY: "auto",
          p: 2,
          display: "flex",
          flexDirection: "column",
          gap: 1,
        }}
      >
        {messages.map((msg) => (
          <ChatBubble key={msg.id} message={msg} />
        ))}
        {loading && (
          <Box
            sx={(t) => ({
              alignSelf: "flex-start",
              px: 1.5,
              py: 1.25,
              borderRadius: "20px",
              bgcolor: t.palette.mode === "dark" ? "rgba(62,145,255,0.1)" : "#EDF4FF",
              border: `1px solid ${t.palette.mode === "dark" ? "rgba(62,145,255,0.2)" : "#B8D4F8"}`,
              display: "flex",
              gap: 0.5,
              alignItems: "center",
            })}
          >
            {[0, 1, 2].map((i) => (
              <Box
                key={i}
                sx={{
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  bgcolor: "primary.main",
                  animation: "oneui-pulse 1.2s ease-in-out infinite",
                  animationDelay: `${i * 0.2}s`,
                }}
              />
            ))}
          </Box>
        )}
      </Box>

      <Box sx={{ borderTop: 1, borderColor: "divider", p: 1.5 }}>
        <Box sx={{ display: "flex", gap: 0.5, mb: 1, flexWrap: "wrap" }}>
          {QUICK_CHIPS.map((chip) => (
            <Chip
              key={chip.label}
              label={chip.label}
              size="small"
              variant="outlined"
              clickable
              onClick={() => dispatch(setInputDraft(chip.draft))}
              sx={{
                fontSize: 10,
                fontWeight: 600,
                borderRadius: "12px",
                "&:hover": { borderColor: "primary.main", color: "primary.main" },
              }}
            />
          ))}
        </Box>
        <Box sx={{ display: "flex", gap: 0.75 }}>
          <TextField
            size="small"
            fullWidth
            placeholder="Ask about staffing, assignments, or crew..."
            value={inputDraft}
            onChange={(e) => dispatch(setInputDraft(e.target.value))}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            disabled={loading}
            sx={{
              "& .MuiOutlinedInput-root": { borderRadius: "16px", fontSize: 12 },
            }}
          />
          <IconButton
            color="primary"
            onClick={handleSend}
            disabled={loading || !inputDraft.trim()}
            sx={{
              background: (t) =>
                t.palette.mode === "dark"
                  ? "linear-gradient(135deg, #3E91FF 0%, #5BABFF 100%)"
                  : "linear-gradient(135deg, #007AFF 0%, #0062CC 100%)",
              color: "white",
              borderRadius: "14px",
              width: 38,
              height: 38,
              "&:hover": {
                background: (t) =>
                  t.palette.mode === "dark"
                    ? "linear-gradient(135deg, #5BABFF 0%, #7DC3FF 100%)"
                    : "linear-gradient(135deg, #0062CC 0%, #004C99 100%)",
              },
              "&.Mui-disabled": { bgcolor: "action.disabledBackground", color: "text.disabled" },
            }}
          >
            <SendIcon sx={{ fontSize: 16 }} />
          </IconButton>
        </Box>
      </Box>
    </Card>
  );
}
