"use client";

import React, { useState, useEffect } from "react";
import {
  Users,
  Send,
  Calendar,
  AlertTriangle,
  Play,
  Pause,
  RotateCcw,
  Search,
  Plus,
  SlidersHorizontal,
  Power,
  Bell,
  Settings,
  ShieldCheck,
  CheckCircle2,
  Inbox as InboxIcon,
  CheckSquare,
  FileCode,
  BookOpen,
  Zap,
  ArrowRight,
  ExternalLink,
  ChevronDown,
  Clock,
  Mail,
  MessageSquare,
  Share2,
  Database,
  FileText,
  Target,
  Download,
  Check,
  X,
  Layers,
  Sparkles,
} from "lucide-react";

export default function HelixControlPlane() {
  const [activeTab, setActiveTab] = useState<
    | "campaigns"
    | "inbox"
    | "approvals"
    | "prospects"
    | "prompts"
    | "knowledge"
    | "runs"
    | "settings"
  >("campaigns");

  const [campaignFilter, setCampaignFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");

  // Notifications Drawer State
  const [showNotifications, setShowNotifications] = useState(false);
  const [apiConnected, setApiConnected] = useState<boolean | null>(null);

  const [notifications, setNotifications] = useState([
    {
      id: "notif-1",
      title: "Human review required",
      message: "Elena Vasquez requires review on compliance claims before sending.",
      time: "2h ago",
      read: false,
      tab: "approvals" as const,
      approvalId: "elena-vasquez",
      priority: "high",
    },
    {
      id: "notif-2",
      title: "Duplicate outreach conflict flagged",
      message: "Elena Vasquez was contacted by another campaign within 14 days.",
      time: "4h ago",
      read: false,
      tab: "prospects" as const,
      approvalId: undefined,
      priority: "medium",
    },
    {
      id: "notif-3",
      title: "Campaign status updated",
      message: "India BFSI CIO was paused by Arjun Mehta.",
      time: "5h ago",
      read: true,
      tab: "campaigns" as const,
      approvalId: undefined,
      priority: "low",
    },
    {
      id: "notif-4",
      title: "Agent telemetry alert",
      message: "2 failed runs retried automatically with Gemini fallback model.",
      time: "6h ago",
      read: true,
      tab: "runs" as const,
      approvalId: undefined,
      priority: "low",
    },
  ]);

  const unreadNotificationsCount = notifications.filter((n) => !n.read).length;

  // Check backend health & sync status
  useEffect(() => {
    let mounted = true;
    const checkBackendHealth = async () => {
      try {
        const res = await fetch("http://localhost:8000/health", {
          mode: "cors",
        });
        if (mounted) {
          setApiConnected(res.ok);
        }
      } catch {
        if (mounted) {
          setApiConnected(false);
        }
      }
    };

    checkBackendHealth();
    const interval = setInterval(checkBackendHealth, 8000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  // Kill switch modal state
  const [showKillSwitchModal, setShowKillSwitchModal] = useState(false);
  const [isPlatformKilled, setIsPlatformKilled] = useState(false);

  // Settings state
  const [settingsTab, setSettingsTab] = useState("global_config");
  const [guardrailToggles, setGuardrailToggles] = useState({
    requireApprovalFirstMessage: true,
    blockDuplicate14Days: true,
    neverSendOutsideWorkingHours: true,
    stopAfterTwoNegativeTurns: true,
    allowPricingFromKnowledge: false,
    allowVoiceWithoutDirectDial: false,
  });

  // Campaigns state
  const [campaigns, setCampaigns] = useState([
    {
      id: "us-saas-cto",
      name: "US SaaS CTO outreach",
      tags: ["SaaS CTO", "Series B+", "United States"],
      status: "live",
      prospects: 1284,
      outreach: 426,
      meetings: 18,
      owner: "Priya Raman",
      ownerInitials: "PR",
      color: "#00d2aa",
    },
    {
      id: "india-bfsi-cio",
      name: "India BFSI CIO",
      tags: ["BFSI CIO", "Enterprise", "India"],
      status: "paused",
      prospects: 642,
      outreach: 211,
      meetings: 11,
      owner: "Arjun Mehta",
      ownerInitials: "AM",
      color: "#f59e0b",
    },
    {
      id: "voice-ai-founders",
      name: "Voice AI founders",
      tags: ["AI founder", "Seed-Series A", "United States"],
      status: "draft",
      prospects: 186,
      outreach: 0,
      meetings: 0,
      owner: "Neha Kulkarni",
      ownerInitials: "NK",
      color: "#6b7280",
    },
  ]);

  // Approvals state
  const [approvalTab, setApprovalTab] = useState("needs_approval");
  const [selectedApprovalId, setSelectedApprovalId] = useState("elena-vasquez");

  const approvals = [
    {
      id: "elena-vasquez",
      name: "Elena Vasquez",
      role: "Chief Technology Officer",
      company: "Meridian Data",
      time: "2h ago",
      subject: "Reply on SOC 2 and data residency",
      type: "email",
      campaign: "US SaaS CTO outreach",
      rule: "human_approval_rules: compliance claims require review",
      draftMessage:
        "Both fair questions. We are SOC 2 Type II, and us-east-1 residency is supported on the standard plan — I have attached the one-pager your security team usually asks for.\n\nIf it helps, I can hold two slots this week: Tue 2:00 PM CT or Thu 10:30 AM CT.",
      guardrails: [
        "No pricing claims",
        "Compliance claims sourced from knowledge base",
        "Meeting times inside rep working hours",
        "Under 140 words",
      ],
      promptVersion: "prompt v7",
      agentStage: "personalisation",
    },
    {
      id: "jonas-berg",
      name: "Jonas Berg",
      role: "VP Engineering",
      company: "Kestrel Cloud",
      time: "4h ago",
      subject: "Case study send after positive reply",
      type: "email",
      campaign: "US SaaS CTO outreach",
      rule: "human_approval_rules: case study verification",
      draftMessage:
        "Great hearing back Jonas! Attached is our benchmark report for scale-stage distributed teams. Would love to run a 15-minute walkthrough of how Acme saved 40 hrs/month.",
      guardrails: [
        "No pricing claims",
        "Case study matches ICP sector",
        "Valid calendar link",
      ],
      promptVersion: "prompt v7",
      agentStage: "personalisation",
    },
    {
      id: "lena-fischer",
      name: "Lena Fischer",
      role: "Director of Infra",
      company: "Apex Tech",
      time: "5h ago",
      subject: "SMS meeting confirmation",
      type: "sms",
      campaign: "US SaaS CTO outreach",
      rule: "human_approval_rules: SMS channel requires explicit opt-in confirmation",
      draftMessage:
        "Hi Lena, this is Priya's team. Confirming our quick demo call for Wednesday at 11am PT. Reply STOP to opt out.",
      guardrails: [
        "Opt-out footer present",
        "Compliant timezone sending hours",
      ],
      promptVersion: "prompt v7",
      agentStage: "outreach",
    },
    {
      id: "felix-andersen",
      name: "Felix Andersen",
      role: "Head of Platform",
      company: "Nordic Wave",
      time: "6h ago",
      subject: "LinkedIn follow-up message",
      type: "linkedin",
      campaign: "US SaaS CTO outreach",
      rule: "human_approval_rules: 3rd touchpoint escalation review",
      draftMessage:
        "Hey Felix, noticed your team just expanded Kubernetes clusters to multi-region. We recently helped a similar team cut cluster idle compute by 32%. Worth a 5-min look?",
      guardrails: [
        "Under 300 characters",
        "Relevant technical trigger verified",
      ],
      promptVersion: "prompt v7",
      agentStage: "followup",
    },
  ];

  // Prospects state
  const [prospectFilter, setProspectFilter] = useState("all");
  const prospects = [
    {
      id: "1",
      name: "Elena Vasquez",
      role: "Chief Technology Officer",
      company: "Meridian Data",
      location: "Austin, United States",
      campaign: "US SaaS CTO outreach",
      campaignStatus: "live",
      fit: 86,
      status: "Contacted",
      conflict: true,
      lastTouch: "2 days ago",
    },
    {
      id: "2",
      name: "Jonas Berg",
      role: "VP Engineering",
      company: "Kestrel Cloud",
      location: "Seattle, United States",
      campaign: "US SaaS CTO outreach",
      campaignStatus: "live",
      fit: 81,
      status: "Engaged",
      conflict: false,
      lastTouch: "6 hours ago",
    },
    {
      id: "3",
      name: "Amara Osei",
      role: "Chief Technology Officer",
      company: "Tessellate",
      location: "Boston, United States",
      campaign: "US SaaS CTO outreach",
      campaignStatus: "live",
      fit: 74,
      status: "Qualified",
      conflict: false,
      lastTouch: "not contacted",
    },
    {
      id: "4",
      name: "Rohit Desai",
      role: "Chief Information Officer",
      company: "Suvarna Bank",
      location: "Mumbai, India",
      campaign: "India BFSI CIO",
      campaignStatus: "paused",
      fit: 79,
      status: "Contacted",
      conflict: false,
      lastTouch: "2 days ago (campaign paused)",
    },
    {
      id: "5",
      name: "Meera Iyer",
      role: "Head of Digital Transformation",
      company: "Arcadia Finserv",
      location: "Bengaluru, India",
      campaign: "India BFSI CIO",
      campaignStatus: "paused",
      fit: 68,
      status: "Researched",
      conflict: false,
      lastTouch: "not contacted",
    },
  ];

  // Prompts state
  const [selectedCampaignForPrompt, setSelectedCampaignForPrompt] =
    useState("us-saas-cto");
  const [selectedPromptType, setSelectedPromptType] =
    useState("campaign-system-prompt");

  const [promptContent, setPromptContent] = useState(`You are the campaign harness for "US SaaS CTO outreach".

TARGET
- ICP: Chief Technology Officer at a B2B SaaS company, Series B or later, 200-2,000 employees.
- Geography: United States and Canada only. Reject anything outside.
- Exclusions: current customers, companies in an active security incident, anyone on the global suppression list.

HOW TO DECIDE
- Never act on the base model alone. Retrieve from campaign knowledge before qualifying a prospect or generating anything customer-facing.
- Qualify only when role fit and company fit both clear 0.70, and you can cite evidence for each.
- If evidence is thin, return decision = "needs_review" rather than guessing.

HOW TO WRITE
- One hook per message, drawn from prospect_research.buying_signals. Never stack two.
- Pair the hook with one customer story from a company of similar size.
- Under 140 words. No adjectives about our own product.
- Close with a single specific ask, not "let me know if you are interested".

GUARDRAILS
- Never state pricing, discounts or contract terms.`);

  const promptVersions = [
    {
      version: "v7",
      active: true,
      notes: "Single-hook rule, evidence thresholds, 14-day duplicate-contact hold",
      author: "Priya Raman",
      date: "19 Sep 2026, 11:20",
    },
    {
      version: "v6",
      active: false,
      notes: "Added compliance guardrail and negative-sentiment escalation",
      author: "Priya Raman",
      date: "17 Sep 2026, 16:05",
    },
    {
      version: "v5",
      active: false,
      notes: "Tightened word limit, removed product adjectives",
      author: "Arjun Mehta",
      date: "16 Sep 2026, 09:42",
    },
    {
      version: "v4",
      active: false,
      notes: "First pass at exclusion criteria",
      author: "Arjun Mehta",
      date: "15 Sep 2026, 14:10",
    },
  ];

  // Knowledge base state
  const [knowledgeCampaignFilter, setKnowledgeCampaignFilter] =
    useState("us-saas-cto");

  const knowledgeDocs = [
    {
      id: "1",
      title: "Case study: Vantage Analytics ETL migration",
      updated: "16 Sep 2026",
      source: "pdf",
      sourceColor: "bg-red-500/10 text-red-400 border-red-500/30",
      chunks: 42,
      tokens: "18,400",
      retrievals: 312,
      status: "Indexed",
    },
    {
      id: "2",
      title: "Sales playbook: SaaS platform consolidation",
      updated: "15 Sep 2026",
      source: "notion",
      sourceColor: "bg-gray-800 text-gray-300 border-gray-700",
      chunks: 88,
      tokens: "39,200",
      retrievals: 498,
      status: "Indexed",
    },
    {
      id: "3",
      title: "Objection handling: security and compliance",
      updated: "17 Sep 2026",
      source: "markdown",
      sourceColor: "bg-blue-500/10 text-blue-400 border-blue-500/30",
      chunks: 26,
      tokens: "11,300",
      retrievals: 203,
      status: "Indexed",
    },
    {
      id: "4",
      title: "SOC 2 and data residency one-pager",
      updated: "12 Sep 2026",
      source: "pdf",
      sourceColor: "bg-red-500/10 text-red-400 border-red-500/30",
      chunks: 9,
      tokens: "4,100",
      retrievals: 87,
      status: "Indexed",
    },
  ];

  const handleToggleCampaign = (id: string) => {
    setCampaigns((prev) =>
      prev.map((c) => {
        if (c.id === id) {
          if (c.status === "live") return { ...c, status: "paused" };
          if (c.status === "paused") return { ...c, status: "live" };
          if (c.status === "draft") return { ...c, status: "live" };
        }
        return c;
      })
    );
  };

  const handleExecuteKillSwitch = () => {
    setIsPlatformKilled(true);
    setCampaigns((prev) => prev.map((c) => ({ ...c, status: "paused" })));
    setShowKillSwitchModal(false);
  };

  const selectedApproval =
    approvals.find((a) => a.id === selectedApprovalId) || approvals[0];

  const wordCount = promptContent.trim().split(/\s+/).length;
  const tokenCount = Math.round(wordCount * 1.6);

  return (
    <div className="min-h-screen bg-[#070b14] text-[#ededed] font-sans antialiased flex flex-col">
      {/* ================= KILL SWITCH ACTIVE BANNER ================= */}
      {isPlatformKilled && (
        <div className="bg-red-600/90 text-white px-6 py-2.5 text-xs font-semibold flex items-center justify-between shadow-lg sticky top-0 z-50">
          <div className="flex items-center gap-2">
            <Power size={14} className="animate-pulse" />
            <span>
              GLOBAL KILL SWITCH ENGAGED — All autonomous agent runs, emails,
              calls and SMS outreach are halted.
            </span>
          </div>
          <button
            onClick={() => setIsPlatformKilled(false)}
            className="px-3 py-1 bg-white text-red-600 rounded text-xs font-bold hover:bg-gray-100 transition shadow"
          >
            Disengage Kill Switch
          </button>
        </div>
      )}

      {/* ================= GLOBAL TOP NAVBAR ================= */}
      <header className="border-b border-gray-800/80 bg-[#0b101e] px-6 py-3 flex items-center justify-between sticky top-0 z-40">
        <div className="flex items-center gap-8">
          {/* Brand Logo */}
          <div
            onClick={() => setActiveTab("campaigns")}
            className="flex items-center gap-2.5 cursor-pointer"
          >
            <div className="w-8 h-8 rounded-lg bg-[#00d2aa]/20 border border-[#00d2aa]/40 flex items-center justify-center text-[#00d2aa]">
              <div className="w-3.5 h-3.5 rounded-full border-2 border-[#00d2aa]" />
            </div>
            <div>
              <span className="font-bold text-base tracking-tight text-white block leading-tight">
                Helix
              </span>
              <span className="text-[11px] text-gray-400 font-medium tracking-wide block leading-none">
                SDR control plane
              </span>
            </div>
          </div>

          {/* Nav Tabs */}
          <nav className="flex items-center gap-1">
            <button
              onClick={() => setActiveTab("campaigns")}
              className={`px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-2 transition-all ${
                activeTab === "campaigns"
                  ? "bg-gray-800 text-white"
                  : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
              }`}
            >
              <Zap
                size={14}
                className={activeTab === "campaigns" ? "text-[#00d2aa]" : ""}
              />
              Campaigns
            </button>

            <button
              onClick={() => setActiveTab("inbox")}
              className={`px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-2 transition-all ${
                activeTab === "inbox"
                  ? "bg-gray-800 text-white"
                  : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
              }`}
            >
              <InboxIcon size={14} />
              Inbox
              <span className="bg-gray-700/80 text-gray-300 text-[10px] px-1.5 py-0.5 rounded-full">
                2
              </span>
            </button>

            <button
              onClick={() => setActiveTab("approvals")}
              className={`px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-2 transition-all ${
                activeTab === "approvals"
                  ? "bg-gray-800 text-white"
                  : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
              }`}
            >
              <CheckSquare size={14} />
              Approvals
              <span className="bg-[#00d2aa]/20 text-[#00d2aa] border border-[#00d2aa]/30 text-[10px] px-1.5 py-0.5 rounded-full font-bold">
                4
              </span>
            </button>

            <button
              onClick={() => setActiveTab("prospects")}
              className={`px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-2 transition-all ${
                activeTab === "prospects"
                  ? "bg-gray-800 text-white"
                  : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
              }`}
            >
              <Users size={14} />
              Prospects
            </button>

            <button
              onClick={() => setActiveTab("prompts")}
              className={`px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-2 transition-all ${
                activeTab === "prompts"
                  ? "bg-gray-800 text-white"
                  : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
              }`}
            >
              <FileCode size={14} />
              Prompts
            </button>

            <button
              onClick={() => setActiveTab("knowledge")}
              className={`px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-2 transition-all ${
                activeTab === "knowledge"
                  ? "bg-gray-800 text-white"
                  : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
              }`}
            >
              <BookOpen size={14} />
              Knowledge
            </button>

            <button
              onClick={() => setActiveTab("runs")}
              className={`px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-2 transition-all ${
                activeTab === "runs"
                  ? "bg-gray-800 text-white"
                  : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
              }`}
            >
              <Zap size={14} />
              Runs
            </button>
          </nav>
        </div>

        {/* Global Controls */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setActiveTab("settings")}
            className={`p-1.5 rounded-md transition ${
              activeTab === "settings"
                ? "bg-gray-800 text-white"
                : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
            }`}
          >
            <Settings size={16} />
          </button>

          {/* Backend Connection Status */}
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-gray-800/80 border border-gray-700/60 text-[11px]">
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                apiConnected
                  ? "bg-emerald-400 animate-pulse"
                  : apiConnected === false
                  ? "bg-amber-400"
                  : "bg-gray-400"
              }`}
            />
            <span className="text-gray-300 font-medium">
              {apiConnected
                ? "Backend Connected"
                : apiConnected === false
                ? "Backend Standby"
                : "Connecting..."}
            </span>
          </div>

          {/* Kill Switch Button */}
          <button
            onClick={() => setShowKillSwitchModal(true)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold border transition-all ${
              isPlatformKilled
                ? "bg-red-500 text-white border-red-600 shadow-lg shadow-red-500/20"
                : "text-red-400 border-red-500/30 hover:bg-red-500/10 hover:border-red-500/60"
            }`}
          >
            <Power size={13} className="text-red-400" />
            {isPlatformKilled ? "Kill switch ACTIVE" : "Kill switch"}
          </button>

          {/* Interactive Notifications Dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowNotifications(!showNotifications)}
              className={`p-1.5 rounded-md transition relative ${
                showNotifications
                  ? "bg-gray-800 text-white"
                  : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
              }`}
            >
              <Bell size={16} />
              {unreadNotificationsCount > 0 && (
                <span className="w-2 h-2 rounded-full bg-amber-400 absolute top-1 right-1 ring-2 ring-[#0b101e]" />
              )}
            </button>

            {showNotifications && (
              <div className="absolute right-0 top-full mt-2 w-80 sm:w-96 bg-[#0b101e] border border-gray-800 rounded-xl shadow-2xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-150">
                <div className="p-3.5 border-b border-gray-800 flex items-center justify-between bg-gray-900/50">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-white text-xs">
                      Notifications
                    </span>
                    {unreadNotificationsCount > 0 && (
                      <span className="bg-amber-500/10 text-amber-400 border border-amber-500/30 text-[10px] px-1.5 py-0.5 rounded font-bold">
                        {unreadNotificationsCount} new
                      </span>
                    )}
                  </div>
                  {unreadNotificationsCount > 0 && (
                    <button
                      onClick={() =>
                        setNotifications((prev) =>
                          prev.map((n) => ({ ...n, read: true }))
                        )
                      }
                      className="text-[11px] text-[#00d2aa] hover:underline font-medium"
                    >
                      Mark all read
                    </button>
                  )}
                </div>

                <div className="divide-y divide-gray-800/60 max-h-80 overflow-y-auto">
                  {notifications.map((n) => (
                    <div
                      key={n.id}
                      onClick={() => {
                        setActiveTab(n.tab);
                        if (n.approvalId) setSelectedApprovalId(n.approvalId);
                        setNotifications((prev) =>
                          prev.map((item) =>
                            item.id === n.id ? { ...item, read: true } : item
                          )
                        );
                        setShowNotifications(false);
                      }}
                      className={`p-3.5 hover:bg-gray-800/40 transition cursor-pointer flex items-start gap-3 ${
                        !n.read ? "bg-[#0f172a]/60" : ""
                      }`}
                    >
                      <div className="mt-0.5 shrink-0">
                        {n.priority === "high" ? (
                          <AlertTriangle size={14} className="text-amber-400" />
                        ) : n.priority === "medium" ? (
                          <ShieldCheck size={14} className="text-blue-400" />
                        ) : (
                          <CheckCircle2 size={14} className="text-emerald-400" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <span
                            className={`text-xs font-semibold truncate ${
                              !n.read ? "text-white" : "text-gray-300"
                            }`}
                          >
                            {n.title}
                          </span>
                          <span className="text-[10px] text-gray-500 shrink-0">
                            {n.time}
                          </span>
                        </div>
                        <p className="text-[11px] text-gray-400 mt-1 leading-snug">
                          {n.message}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="p-2.5 border-t border-gray-800 text-center bg-gray-900/30">
                  <span className="text-[10px] text-gray-500">
                    Click any alert to navigate directly to that view
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* User Profile */}
          <div className="w-7 h-7 rounded-full bg-emerald-700 border border-emerald-500/40 text-emerald-100 flex items-center justify-center text-xs font-bold">
            PR
          </div>
        </div>
      </header>

      {/* ================= MAIN CONTENT AREA ================= */}
      <main className="flex-1 p-8 max-w-7xl mx-auto w-full">
        {/* VIEW 1: CAMPAIGNS */}
        {activeTab === "campaigns" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold tracking-tight text-white">
                  Campaigns
                </h1>
                <p className="text-xs text-gray-400 mt-1">
                  3 campaigns • 1 live • 1 paused • 1 in draft
                </p>
              </div>

              <div className="flex items-center gap-3">
                <button className="px-3.5 py-1.5 rounded-lg border border-gray-700 bg-gray-800/80 hover:bg-gray-800 text-xs font-medium text-gray-300 transition flex items-center gap-1.5">
                  <SlidersHorizontal size={13} />
                  Compare
                </button>
                <button className="px-3.5 py-1.5 rounded-lg bg-[#00d2aa] hover:bg-[#00be99] text-gray-950 text-xs font-semibold transition flex items-center gap-1.5 shadow-lg shadow-[#00d2aa]/20">
                  <Plus size={14} />
                  New campaign
                </button>
              </div>
            </div>

            {/* Stat Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-[#0f172a]/60 border border-gray-800/80 rounded-xl p-5 relative overflow-hidden">
                <div className="flex items-center gap-2 text-gray-400 text-xs font-medium mb-3">
                  <Users size={14} className="text-indigo-400" />
                  Prospects
                </div>
                <div className="text-3xl font-extrabold text-white tracking-tight">
                  2,112
                </div>
                <div className="text-[11px] text-gray-500 mt-1.5">
                  148 added this week
                </div>
              </div>

              <div className="bg-[#0f172a]/60 border border-gray-800/80 rounded-xl p-5 relative overflow-hidden">
                <div className="flex items-center gap-2 text-gray-400 text-xs font-medium mb-3">
                  <Send size={14} className="text-blue-400" />
                  Outreach sent
                </div>
                <div className="text-3xl font-extrabold text-white tracking-tight">
                  637
                </div>
                <div className="text-[11px] text-gray-500 mt-1.5">
                  63 today across 4 channels
                </div>
              </div>

              <div className="bg-[#0f172a]/60 border border-gray-800/80 rounded-xl p-5 relative overflow-hidden">
                <div className="flex items-center gap-2 text-gray-400 text-xs font-medium mb-3">
                  <Calendar size={14} className="text-cyan-400" />
                  Meetings booked
                </div>
                <div className="text-3xl font-extrabold text-white tracking-tight">
                  29
                </div>
                <div className="text-[11px] text-gray-500 mt-1.5">
                  4.6% of contacted prospects
                </div>
              </div>

              <div className="bg-[#0f172a]/60 border border-gray-800/80 rounded-xl p-5 relative overflow-hidden">
                <div className="flex items-center gap-2 text-amber-400 text-xs font-medium mb-3">
                  <AlertTriangle size={14} />
                  Needs attention
                </div>
                <div className="text-3xl font-extrabold text-amber-400 tracking-tight">
                  13
                </div>
                <div className="text-[11px] text-gray-500 mt-1.5">
                  7 escalations, 4 approvals, 2 failed
                </div>
              </div>
            </div>

            {/* Filter Tabs & Search */}
            <div className="flex items-center justify-between pt-2">
              <div className="flex items-center gap-2">
                {[
                  { label: "All", count: 3, value: "all" },
                  { label: "Live", count: 1, value: "live" },
                  { label: "Paused", count: 1, value: "paused" },
                  { label: "Draft", count: 1, value: "draft" },
                  { label: "Completed", count: 0, value: "completed" },
                ].map((pill) => (
                  <button
                    key={pill.value}
                    onClick={() => setCampaignFilter(pill.value)}
                    className={`px-3 py-1 rounded-full text-xs font-medium transition flex items-center gap-1.5 ${
                      campaignFilter === pill.value
                        ? "bg-[#00d2aa]/20 border border-[#00d2aa]/50 text-[#00d2aa]"
                        : "bg-gray-800/60 border border-gray-800 text-gray-400 hover:text-gray-200"
                    }`}
                  >
                    {pill.label}
                    <span className="text-[10px] opacity-75">{pill.count}</span>
                  </button>
                ))}
              </div>

              <div className="relative w-72">
                <Search
                  size={14}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500"
                />
                <input
                  type="text"
                  placeholder="Search campaigns or ICP"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-[#0b101e] border border-gray-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-[#00d2aa]/60"
                />
              </div>
            </div>

            {/* Campaigns Table */}
            <div className="bg-[#0b101e] border border-gray-800/80 rounded-xl overflow-hidden shadow-xl">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-gray-800/80 text-gray-400 font-semibold bg-gray-900/40">
                    <th className="py-3 px-4">Campaign</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Prospects</th>
                    <th className="py-3 px-4">Outreach</th>
                    <th className="py-3 px-4">Meetings</th>
                    <th className="py-3 px-4">Owner</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60">
                  {campaigns
                    .filter(
                      (c) =>
                        campaignFilter === "all" || c.status === campaignFilter
                    )
                    .map((camp) => (
                      <tr
                        key={camp.id}
                        className="hover:bg-gray-800/30 transition group cursor-pointer"
                      >
                        <td className="py-4 px-4 relative">
                          <div
                            className="absolute left-0 top-0 bottom-0 w-1"
                            style={{ backgroundColor: camp.color }}
                          />
                          <div className="font-semibold text-white text-sm">
                            {camp.name}
                          </div>
                          <div className="flex items-center gap-1.5 mt-1.5">
                            {camp.tags.map((tag) => (
                              <span
                                key={tag}
                                className="bg-gray-800/90 text-gray-400 text-[10px] px-2 py-0.5 rounded border border-gray-700/60"
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                        </td>

                        <td className="py-4 px-4">
                          {camp.status === "live" && (
                            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                              Live
                            </span>
                          )}
                          {camp.status === "paused" && (
                            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
                              <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                              Paused
                            </span>
                          )}
                          {camp.status === "draft" && (
                            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium bg-gray-500/10 text-gray-400 border border-gray-500/20">
                              <span className="w-1.5 h-1.5 rounded-full bg-gray-400" />
                              Draft
                            </span>
                          )}
                        </td>

                        <td className="py-4 px-4 font-medium text-gray-300">
                          {camp.prospects.toLocaleString()}{" "}
                          <span className="text-[11px] text-gray-500">
                            prospects
                          </span>
                        </td>

                        <td className="py-4 px-4 font-medium text-gray-300">
                          {camp.outreach}{" "}
                          <span className="text-[11px] text-gray-500">sent</span>
                        </td>

                        <td className="py-4 px-4 font-medium text-gray-300">
                          {camp.meetings}{" "}
                          <span className="text-[11px] text-gray-500">
                            meetings
                          </span>
                        </td>

                        <td className="py-4 px-4">
                          <div className="flex items-center gap-2">
                            <span className="w-6 h-6 rounded-full bg-indigo-900/60 border border-indigo-500/30 text-indigo-300 flex items-center justify-center text-[10px] font-bold">
                              {camp.ownerInitials}
                            </span>
                            <span className="text-gray-300 font-medium">
                              {camp.owner}
                            </span>
                          </div>
                        </td>

                        <td className="py-4 px-4 text-right">
                          {camp.status === "live" && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleToggleCampaign(camp.id);
                              }}
                              className="px-3 py-1 rounded border border-amber-500/40 bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 font-semibold text-xs transition inline-flex items-center gap-1"
                            >
                              <Pause size={11} />
                              Pause
                            </button>
                          )}
                          {camp.status === "paused" && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleToggleCampaign(camp.id);
                              }}
                              className="px-3 py-1 rounded border border-emerald-500/40 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 font-semibold text-xs transition inline-flex items-center gap-1"
                            >
                              <Play size={11} />
                              Resume
                            </button>
                          )}
                          {camp.status === "draft" && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleToggleCampaign(camp.id);
                              }}
                              className="px-3 py-1 rounded border border-[#00d2aa]/40 bg-[#00d2aa]/10 hover:bg-[#00d2aa]/20 text-[#00d2aa] font-semibold text-xs transition inline-flex items-center gap-1"
                            >
                              <Play size={11} />
                              Activate
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>

            <div className="text-center text-xs text-gray-500 pt-1">
              Click any row to open its dashboard, agents and live activity.
            </div>
          </div>
        )}

        {/* VIEW 2: APPROVALS */}
        {activeTab === "approvals" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold tracking-tight text-white">
                  Approvals
                </h1>
                <p className="text-xs text-gray-400 mt-1">
                  Everything the agents stopped and handed to a human, across all
                  campaigns.
                </p>
              </div>

              <button
                onClick={() => setActiveTab("settings")}
                className="px-3.5 py-1.5 rounded-lg border border-gray-700 bg-gray-800/80 hover:bg-gray-800 text-xs font-medium text-gray-300 transition flex items-center gap-1.5"
              >
                <Settings size={13} />
                Approval rules
              </button>
            </div>

            {/* Approval Sub-Tabs */}
            <div className="flex items-center gap-2 border-b border-gray-800/80 pb-3">
              {[
                { id: "needs_approval", label: "Needs approval", count: 4 },
                { id: "escalations", label: "Escalations", count: 7 },
                { id: "failed_runs", label: "Failed runs", count: 2 },
                { id: "all", label: "All", count: 13 },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setApprovalTab(tab.id)}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition flex items-center gap-1.5 ${
                    approvalTab === tab.id
                      ? "bg-[#00d2aa]/20 border border-[#00d2aa]/50 text-[#00d2aa]"
                      : "text-gray-400 hover:text-gray-200"
                  }`}
                >
                  {tab.label}
                  <span className="text-[10px] opacity-75">{tab.count}</span>
                </button>
              ))}
            </div>

            {/* Split Screen Master-Detail */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-start">
              <div className="md:col-span-5 space-y-3">
                {approvals.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => setSelectedApprovalId(item.id)}
                    className={`p-4 rounded-xl border transition cursor-pointer relative ${
                      selectedApprovalId === item.id
                        ? "bg-[#0f172a] border-[#00d2aa]/40 shadow-lg"
                        : "bg-[#0b101e] border-gray-800/80 hover:border-gray-700"
                    }`}
                  >
                    {selectedApprovalId === item.id && (
                      <div className="absolute left-0 top-3 bottom-3 w-1 bg-[#00d2aa] rounded-r" />
                    )}

                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-semibold text-white text-sm">
                        {item.name}
                      </span>
                      <span className="text-gray-500 text-[11px] flex items-center gap-1">
                        <Clock size={11} /> {item.time}
                      </span>
                    </div>

                    <div className="text-xs text-gray-300 font-medium line-clamp-1 mb-2">
                      {item.subject}
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="bg-amber-500/10 border border-amber-500/30 text-amber-400 text-[10px] px-2 py-0.5 rounded font-semibold">
                        Needs approval
                      </span>
                      <span className="bg-gray-800 text-gray-400 text-[10px] px-2 py-0.5 rounded border border-gray-700">
                        {item.type}
                      </span>
                      <span className="text-gray-500 text-[11px] truncate">
                        {item.campaign}
                      </span>
                    </div>
                  </div>
                ))}
              </div>

              <div className="md:col-span-7 bg-[#0b101e] border border-gray-800/80 rounded-xl p-6 shadow-xl space-y-6">
                <div className="flex items-start justify-between border-b border-gray-800 pb-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs px-2.5 py-0.5 rounded font-semibold">
                        Needs approval
                      </span>
                      <h2 className="text-base font-bold text-white">
                        {selectedApproval.subject}
                      </h2>
                    </div>
                    <div className="text-xs text-gray-400">
                      {selectedApproval.name} • {selectedApproval.campaign} •{" "}
                      {selectedApproval.time}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="bg-gray-800 text-gray-300 text-xs px-2.5 py-1 rounded border border-gray-700">
                      {selectedApproval.agentStage}
                    </span>
                    <span className="bg-gray-800 text-gray-400 text-xs px-2.5 py-1 rounded border border-gray-700">
                      {selectedApproval.promptVersion}
                    </span>
                  </div>
                </div>

                <div>
                  <div className="text-xs font-semibold text-gray-400 mb-2">
                    Why a human is needed
                  </div>
                  <div className="bg-[#070b14] border border-gray-800 rounded-lg p-3 text-xs font-mono text-amber-300/90">
                    {selectedApproval.rule}
                  </div>
                </div>

                <div>
                  <div className="text-xs font-semibold text-gray-400 mb-2">
                    Message the agent wants to send
                  </div>
                  <div className="bg-[#070b14] border border-gray-800 rounded-lg p-4 text-xs text-gray-200 leading-relaxed whitespace-pre-wrap">
                    {selectedApproval.draftMessage}
                  </div>
                </div>

                <div>
                  <div className="text-xs font-semibold text-gray-400 mb-2.5">
                    Guardrails passed
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {selectedApproval.guardrails.map((g, i) => (
                      <span
                        key={i}
                        className="inline-flex items-center gap-1.5 bg-emerald-950/40 border border-emerald-500/30 text-emerald-400 text-[11px] px-2.5 py-1 rounded-md font-medium"
                      >
                        <CheckCircle2 size={12} className="text-emerald-400" />
                        {g}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-800">
                  <button className="px-4 py-2 rounded-lg border border-gray-700 bg-gray-800/80 hover:bg-gray-800 text-xs font-medium text-gray-300 transition">
                    Reject
                  </button>
                  <button className="px-4 py-2 rounded-lg border border-gray-700 bg-gray-800/80 hover:bg-gray-800 text-xs font-medium text-gray-300 transition">
                    Edit
                  </button>
                  <button className="px-4 py-2 rounded-lg bg-[#00d2aa] hover:bg-[#00be99] text-gray-950 text-xs font-bold transition shadow-lg shadow-[#00d2aa]/20">
                    Approve and send
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* VIEW 3: PROSPECTS */}
        {activeTab === "prospects" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold tracking-tight text-white">
                  Prospects
                </h1>
                <p className="text-xs text-gray-400 mt-1">
                  7 prospects across 3 campaigns • 1 flagged for duplicate
                  outreach
                </p>
              </div>

              <button className="px-3.5 py-1.5 rounded-lg bg-[#00d2aa] hover:bg-[#00be99] text-gray-950 text-xs font-bold transition flex items-center gap-1.5 shadow-lg shadow-[#00d2aa]/20">
                <Plus size={14} />
                Import prospects
              </button>
            </div>

            <div className="flex items-center gap-2">
              {[
                { id: "all", label: "All", count: 7 },
                { id: "us-saas-cto", label: "US SaaS CTO outreach", count: 4 },
                { id: "india-bfsi-cio", label: "India BFSI CIO", count: 2 },
                { id: "voice-ai-founders", label: "Voice AI founders", count: 1 },
              ].map((pill) => (
                <button
                  key={pill.id}
                  onClick={() => setProspectFilter(pill.id)}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition flex items-center gap-1.5 ${
                    prospectFilter === pill.id
                      ? "bg-[#00d2aa]/20 border border-[#00d2aa]/50 text-[#00d2aa]"
                      : "bg-gray-800/60 border border-gray-800 text-gray-400 hover:text-gray-200"
                  }`}
                >
                  {pill.label}
                  <span className="text-[10px] opacity-75">{pill.count}</span>
                </button>
              ))}
            </div>

            <div className="bg-[#0b101e] border border-gray-800/80 rounded-xl overflow-hidden shadow-xl">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-gray-800/80 text-gray-400 font-semibold bg-gray-900/40">
                    <th className="py-3 px-4">Prospect</th>
                    <th className="py-3 px-4">Company</th>
                    <th className="py-3 px-4">Campaign</th>
                    <th className="py-3 px-4">Fit</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4 text-right">Last touch</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60">
                  {prospects.map((p) => (
                    <tr key={p.id} className="hover:bg-gray-800/30 transition">
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-white">{p.name}</div>
                        <div className="text-[11px] text-gray-400">{p.role}</div>
                      </td>

                      <td className="py-3.5 px-4">
                        <div className="text-gray-200 font-medium">
                          {p.company}
                        </div>
                        <div className="text-[11px] text-gray-500">
                          {p.location}
                        </div>
                      </td>

                      <td className="py-3.5 px-4">
                        <div className="text-gray-300 font-medium flex items-center gap-1.5">
                          {p.campaign}
                        </div>
                        <span className="text-[10px] text-emerald-400 flex items-center gap-1 mt-0.5">
                          <span className="w-1 h-1 rounded-full bg-emerald-400" />
                          {p.campaignStatus === "live" ? "Live" : "Paused"}
                        </span>
                      </td>

                      <td className="py-3.5 px-4">
                        <span
                          className={`font-bold text-sm ${
                            p.fit >= 75 ? "text-emerald-400" : "text-amber-400"
                          }`}
                        >
                          {p.fit}
                        </span>
                      </td>

                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-1.5">
                          <span className="bg-gray-800 text-gray-300 px-2 py-0.5 rounded border border-gray-700 text-[10px] font-medium">
                            {p.status}
                          </span>
                          {p.conflict && (
                            <span className="bg-amber-500/10 text-amber-400 border border-amber-500/30 px-1.5 py-0.5 rounded text-[10px] font-bold">
                              conflict
                            </span>
                          )}
                        </div>
                      </td>

                      <td className="py-3.5 px-4 text-right text-gray-400 text-[11px]">
                        {p.lastTouch}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* VIEW 4: PROMPTS */}
        {activeTab === "prompts" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold tracking-tight text-white">
                  Prompts
                </h1>
                <p className="text-xs text-gray-400 mt-1">
                  Edit the harness, version every change, and roll back without
                  touching another campaign.
                </p>
              </div>

              <div className="flex items-center gap-3">
                <select
                  value={selectedCampaignForPrompt}
                  onChange={(e) => setSelectedCampaignForPrompt(e.target.value)}
                  className="bg-[#0b101e] border border-gray-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-[#00d2aa]"
                >
                  <option value="us-saas-cto">US SaaS CTO outreach</option>
                  <option value="india-bfsi-cio">India BFSI CIO</option>
                  <option value="voice-ai-founders">Voice AI founders</option>
                </select>

                <select
                  value={selectedPromptType}
                  onChange={(e) => setSelectedPromptType(e.target.value)}
                  className="bg-[#0b101e] border border-gray-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-[#00d2aa]"
                >
                  <option value="campaign-system-prompt">
                    Campaign system prompt
                  </option>
                  <option value="icp-fitment-prompt">ICP Fitment Agent</option>
                  <option value="lead-research-prompt">
                    Lead Research Agent
                  </option>
                  <option value="personalization-prompt">
                    Personalisation Agent
                  </option>
                </select>

                <button className="px-3 py-1.5 rounded-lg border border-gray-700 bg-gray-800/80 hover:bg-gray-800 text-xs font-medium text-gray-300 transition flex items-center gap-1">
                  Open campaign <ArrowRight size={12} />
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-start">
              <div className="md:col-span-8 bg-[#0b101e] border border-gray-800/80 rounded-xl p-5 shadow-xl space-y-4">
                <div className="flex items-center justify-between border-b border-gray-800 pb-3">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-white text-sm">
                      Campaign system prompt
                    </span>
                    <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-[10px] px-2 py-0.5 rounded-full font-semibold">
                      • v7 active
                    </span>
                  </div>

                  <div className="text-xs text-gray-400 font-mono">
                    {wordCount} words • ~{tokenCount} tokens
                  </div>
                </div>

                <textarea
                  rows={18}
                  value={promptContent}
                  onChange={(e) => setPromptContent(e.target.value)}
                  className="w-full bg-[#070b14] border border-gray-800/80 rounded-lg p-4 font-mono text-xs text-gray-200 leading-relaxed focus:outline-none focus:border-[#00d2aa]/60 resize-none"
                />

                <div className="flex items-center justify-between pt-2">
                  <span className="text-[11px] text-gray-500">
                    Changes create an incremental version automatically.
                  </span>
                  <button className="px-4 py-1.5 rounded-lg bg-[#00d2aa] hover:bg-[#00be99] text-gray-950 text-xs font-bold transition shadow-lg shadow-[#00d2aa]/20">
                    Save as v8
                  </button>
                </div>
              </div>

              <div className="md:col-span-4 bg-[#0b101e] border border-gray-800/80 rounded-xl p-5 shadow-xl space-y-4">
                <div className="flex items-center justify-between border-b border-gray-800 pb-3">
                  <span className="font-semibold text-white text-sm">
                    Version history
                  </span>
                  <span className="text-xs text-gray-400">7 versions</span>
                </div>

                <div className="space-y-3">
                  {promptVersions.map((v) => (
                    <div
                      key={v.version}
                      className={`p-3 rounded-lg border transition ${
                        v.active
                          ? "bg-[#0f172a] border-[#00d2aa]/40"
                          : "bg-[#070b14]/50 border-gray-800/80"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span
                          className={`text-xs font-bold ${
                            v.active ? "text-[#00d2aa]" : "text-white"
                          }`}
                        >
                          {v.version}
                        </span>
                        {v.active ? (
                          <span className="text-[10px] text-[#00d2aa] font-medium">
                            in use
                          </span>
                        ) : (
                          <button className="text-[10px] text-gray-400 hover:text-white px-2 py-0.5 rounded bg-gray-800 border border-gray-700">
                            Roll back
                          </button>
                        )}
                      </div>

                      <div className="text-xs text-gray-300 mb-1.5 leading-snug">
                        {v.notes}
                      </div>

                      <div className="text-[10px] text-gray-500">
                        {v.author} • {v.date}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* VIEW 5: KNOWLEDGE (Screenshot 1) */}
        {activeTab === "knowledge" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold tracking-tight text-white">
                  Knowledge
                </h1>
                <p className="text-xs text-gray-400 mt-1">
                  What agents retrieve from before they qualify anyone or write
                  anything customer facing.
                </p>
              </div>

              <button className="px-3.5 py-1.5 rounded-lg bg-[#00d2aa] hover:bg-[#00be99] text-gray-950 text-xs font-bold transition flex items-center gap-1.5 shadow-lg shadow-[#00d2aa]/20">
                <Plus size={14} />
                Add document
              </button>
            </div>

            {/* Knowledge Stat Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-[#0f172a]/60 border border-gray-800/80 rounded-xl p-5 relative overflow-hidden">
                <div className="flex items-center gap-2 text-gray-400 text-xs font-medium mb-3">
                  <FileText size={14} className="text-gray-400" />
                  Documents
                </div>
                <div className="text-3xl font-extrabold text-white tracking-tight">
                  7
                </div>
                <div className="text-[11px] text-gray-500 mt-1.5">6 active</div>
              </div>

              <div className="bg-[#0f172a]/60 border border-gray-800/80 rounded-xl p-5 relative overflow-hidden">
                <div className="flex items-center gap-2 text-emerald-400 text-xs font-medium mb-3">
                  <Layers size={14} />
                  Chunks
                </div>
                <div className="text-3xl font-extrabold text-white tracking-tight">
                  216
                </div>
                <div className="text-[11px] text-gray-500 mt-1.5">
                  embedding vector(768)
                </div>
              </div>

              <div className="bg-[#0f172a]/60 border border-gray-800/80 rounded-xl p-5 relative overflow-hidden">
                <div className="flex items-center gap-2 text-gray-400 text-xs font-medium mb-3">
                  <Database size={14} className="text-blue-400" />
                  Indexed tokens
                </div>
                <div className="text-3xl font-extrabold text-white tracking-tight">
                  93,400
                </div>
                <div className="text-[11px] text-gray-500 mt-1.5">
                  across this campaign
                </div>
              </div>

              <div className="bg-[#0f172a]/60 border border-gray-800/80 rounded-xl p-5 relative overflow-hidden">
                <div className="flex items-center gap-2 text-pink-400 text-xs font-medium mb-3">
                  <Target size={14} />
                  Retrieval hit rate
                </div>
                <div className="text-3xl font-extrabold text-white tracking-tight">
                  94%
                </div>
                <div className="text-[11px] text-gray-500 mt-1.5">
                  decisions citing a source
                </div>
              </div>
            </div>

            {/* Campaign Selection Tabs */}
            <div className="flex items-center gap-2 pt-1">
              {[
                { id: "us-saas-cto", label: "US SaaS CTO outreach" },
                { id: "india-bfsi-cio", label: "India BFSI CIO" },
                { id: "voice-ai-founders", label: "Voice AI founders" },
              ].map((c) => (
                <button
                  key={c.id}
                  onClick={() => setKnowledgeCampaignFilter(c.id)}
                  className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition ${
                    knowledgeCampaignFilter === c.id
                      ? "bg-[#0b101e] border border-gray-700 text-white font-semibold"
                      : "text-gray-400 hover:text-gray-200"
                  }`}
                >
                  {c.label}
                </button>
              ))}
            </div>

            {/* Knowledge Table */}
            <div className="bg-[#0b101e] border border-gray-800/80 rounded-xl overflow-hidden shadow-xl">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-gray-800/80 text-gray-400 font-semibold bg-gray-900/40">
                    <th className="py-3 px-4">Document</th>
                    <th className="py-3 px-4">Source</th>
                    <th className="py-3 px-4">Chunks</th>
                    <th className="py-3 px-4">Tokens</th>
                    <th className="py-3 px-4">Retrievals</th>
                    <th className="py-3 px-4 text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60">
                  {knowledgeDocs.map((doc) => (
                    <tr
                      key={doc.id}
                      className="hover:bg-gray-800/30 transition cursor-pointer"
                    >
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-white">{doc.title}</div>
                        <div className="text-[11px] text-gray-500">
                          updated {doc.updated}
                        </div>
                      </td>

                      <td className="py-3.5 px-4">
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded border uppercase font-mono font-semibold ${doc.sourceColor}`}
                        >
                          {doc.source}
                        </span>
                      </td>

                      <td className="py-3.5 px-4 font-medium text-gray-300">
                        {doc.chunks}
                      </td>

                      <td className="py-3.5 px-4 font-medium text-gray-300">
                        {doc.tokens}
                      </td>

                      <td className="py-3.5 px-4 font-medium text-gray-300">
                        {doc.retrievals}
                      </td>

                      <td className="py-3.5 px-4 text-right">
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                          {doc.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* VIEW 6: RUNS (Screenshot 2) */}
        {activeTab === "runs" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold tracking-tight text-white">
                  Agent runs
                </h1>
                <p className="text-xs text-gray-400 mt-1">
                  Cost, latency and model routing for every decision the system
                  made today.
                </p>
              </div>

              <button className="px-3.5 py-1.5 rounded-lg border border-gray-700 bg-gray-800/80 hover:bg-gray-800 text-xs font-medium text-gray-300 transition flex items-center gap-1.5">
                <Download size={13} />
                Export runs
              </button>
            </div>

            {/* Runs Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
              <div className="bg-[#0f172a]/60 border border-gray-800/80 rounded-xl p-5 relative overflow-hidden">
                <div className="flex items-center gap-2 text-gray-400 text-xs font-medium mb-3">
                  <Zap size={14} className="text-amber-400" />
                  Runs today
                </div>
                <div className="text-3xl font-extrabold text-white tracking-tight">
                  1,254
                </div>
                <div className="text-[11px] text-gray-500 mt-1.5">
                  across 7 agent types
                </div>
              </div>

              <div className="bg-[#0f172a]/60 border border-gray-800/80 rounded-xl p-5 relative overflow-hidden">
                <div className="flex items-center gap-2 text-gray-400 text-xs font-medium mb-3">
                  <Clock size={14} className="text-[#00d2aa]" />
                  Median latency
                </div>
                <div className="text-3xl font-extrabold text-white tracking-tight">
                  1.7s
                </div>
                <div className="text-[11px] text-gray-500 mt-1.5">
                  text agents, excluding voice
                </div>
              </div>

              <div className="bg-[#0f172a]/60 border border-gray-800/80 rounded-xl p-5 relative overflow-hidden">
                <div className="flex items-center gap-2 text-gray-400 text-xs font-medium mb-3">
                  <Layers size={14} className="text-blue-400" />
                  Tokens today
                </div>
                <div className="text-3xl font-extrabold text-white tracking-tight">
                  67k
                </div>
                <div className="text-[11px] text-gray-500 mt-1.5">
                  in + out, all models
                </div>
              </div>

              <div className="bg-[#0f172a]/60 border border-gray-800/80 rounded-xl p-5 relative overflow-hidden">
                <div className="flex items-center gap-2 text-gray-400 text-xs font-medium mb-3">
                  <CheckCircle2 size={14} className="text-emerald-400" />
                  Spend today
                </div>
                <div className="text-3xl font-extrabold text-emerald-400 tracking-tight">
                  $14.82
                </div>
                <div className="text-[11px] text-gray-500 mt-1.5">
                  $0.42 per qualified lead
                </div>
              </div>

              <div className="bg-[#0f172a]/60 border border-gray-800/80 rounded-xl p-5 relative overflow-hidden">
                <div className="flex items-center gap-2 text-amber-400 text-xs font-medium mb-3">
                  <AlertTriangle size={14} />
                  Failure rate
                </div>
                <div className="text-3xl font-extrabold text-amber-400 tracking-tight">
                  12.5%
                </div>
                <div className="text-[11px] text-gray-500 mt-1.5">
                  2 failed runs, both retried
                </div>
              </div>
            </div>

            {/* Split Section: Model Routing & Latency By Agent */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-start">
              {/* Left Column: Model Routing */}
              <div className="md:col-span-6 bg-[#0b101e] border border-gray-800/80 rounded-xl p-5 shadow-xl space-y-4">
                <div className="flex items-center justify-between border-b border-gray-800 pb-3">
                  <span className="font-semibold text-white text-sm">
                    Model routing
                  </span>
                  <span className="text-xs text-gray-400">
                    smaller models where quality allows
                  </span>
                </div>

                <div className="space-y-3.5">
                  {[
                    {
                      name: "icp fitment",
                      badge: "Haiku 4.5",
                      badgeColor: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
                      description: "Cheap classification, structured output only",
                      runs: "412 runs",
                      latency: "1.2s",
                      cost: "$0.0020",
                    },
                    {
                      name: "outreach_strategy",
                      badge: "Haiku 4.5",
                      badgeColor: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
                      description: "Rule-heavy decision, no generation",
                      runs: "196 runs",
                      latency: "0.9s",
                      cost: "$0.0016",
                    },
                    {
                      name: "followup",
                      badge: "Haiku 4.5",
                      badgeColor: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
                      description: "Scheduling logic, no customer facing text",
                      runs: "121 runs",
                      latency: "0.7s",
                      cost: "$0.0013",
                    },
                    {
                      name: "lead_research",
                      badge: "Sonnet 5",
                      badgeColor: "bg-indigo-500/10 text-indigo-400 border-indigo-500/30",
                      description: "Multi-source synthesis, long context",
                      runs: "288 runs",
                      latency: "4.8s",
                      cost: "$0.0322",
                    },
                    {
                      name: "personalisation",
                      badge: "Sonnet 5",
                      badgeColor: "bg-indigo-500/10 text-indigo-400 border-indigo-500/30",
                      description: "Customer-facing text, quality matters",
                      runs: "174 runs",
                      latency: "2.4s",
                      cost: "$0.0139",
                    },
                  ].map((item) => (
                    <div
                      key={item.name}
                      className="flex items-center justify-between border-b border-gray-800/50 pb-3 last:border-0"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-white text-xs">
                            {item.name}
                          </span>
                          <span
                            className={`text-[10px] px-1.5 py-0.5 rounded border font-mono ${item.badgeColor}`}
                          >
                            {item.badge}
                          </span>
                        </div>
                        <div className="text-[11px] text-gray-500 mt-0.5">
                          {item.description}
                        </div>
                      </div>

                      <div className="text-right text-xs font-mono">
                        <div className="text-gray-300 font-medium">
                          {item.runs} • {item.latency}
                        </div>
                        <div className="text-gray-500 text-[11px]">
                          {item.cost}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Right Column: Latency by Agent */}
              <div className="md:col-span-6 bg-[#0b101e] border border-gray-800/80 rounded-xl p-5 shadow-xl space-y-4">
                <div className="flex items-center justify-between border-b border-gray-800 pb-3">
                  <span className="font-semibold text-white text-sm">
                    Latency by agent
                  </span>
                </div>

                <div className="space-y-4 pt-1">
                  {[
                    { name: "icp_fitment", width: "24%", latency: "1.2s", color: "bg-[#00d2aa]" },
                    { name: "outreach strategy", width: "18%", latency: "0.9s", color: "bg-[#00d2aa]" },
                    { name: "followup", width: "14%", latency: "0.7s", color: "bg-[#00d2aa]" },
                    { name: "lead research", width: "70%", latency: "4.8s", color: "bg-[#00d2aa]" },
                    { name: "personalisation", width: "42%", latency: "2.4s", color: "bg-[#00d2aa]" },
                    { name: "conversation", width: "30%", latency: "1.6s", color: "bg-[#00d2aa]" },
                    { name: "voice_sdr", width: "95%", latency: "42s", color: "bg-amber-400" },
                  ].map((row) => (
                    <div key={row.name} className="space-y-1.5">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-300 font-medium">
                          {row.name}
                        </span>
                        <span className="font-mono text-gray-400">
                          {row.latency}
                        </span>
                      </div>
                      <div className="w-full bg-[#070b14] rounded-full h-2 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${row.color}`}
                          style={{ width: row.width }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* VIEW 7: SETTINGS (Screenshot 3) */}
        {activeTab === "settings" && (
          <div className="space-y-6 max-w-4xl">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white">
                Settings
              </h1>
              <p className="text-xs text-gray-400 mt-1">
                Platform-wide configuration. Campaign-level settings live on each
                campaign.
              </p>
            </div>

            {/* Settings Sub-Tabs */}
            <div className="flex items-center gap-2 border-b border-gray-800/80 pb-3">
              {[
                { id: "global_config", label: "Global config" },
                { id: "integrations", label: "Integrations" },
                { id: "representatives", label: "Representatives" },
                { id: "suppression_list", label: "Suppression list" },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setSettingsTab(tab.id)}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition ${
                    settingsTab === tab.id
                      ? "bg-[#00d2aa]/20 border border-[#00d2aa]/50 text-[#00d2aa]"
                      : "text-gray-400 hover:text-gray-200"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Platform Guardrails Section */}
            <div className="bg-[#0b101e] border border-gray-800/80 rounded-xl p-6 shadow-xl space-y-5">
              <div className="border-b border-gray-800 pb-3">
                <h2 className="font-semibold text-white text-sm">
                  Platform guardrails
                </h2>
                <p className="text-xs text-gray-400 mt-0.5">
                  Applied to every campaign. A campaign can narrow these, never
                  loosen them.
                </p>
              </div>

              <div className="space-y-4">
                {[
                  {
                    key: "requireApprovalFirstMessage",
                    label:
                      "Require approval before the first message on any new channel",
                  },
                  {
                    key: "blockDuplicate14Days",
                    label:
                      "Block outreach to anyone contacted by another campaign in the last 14 days",
                  },
                  {
                    key: "neverSendOutsideWorkingHours",
                    label: "Never send outside a rep working hours",
                  },
                  {
                    key: "stopAfterTwoNegativeTurns",
                    label:
                      "Stop autonomous handling after two negative turns in a thread",
                  },
                  {
                    key: "allowPricingFromKnowledge",
                    label:
                      "Allow agents to state pricing from the knowledge base",
                  },
                  {
                    key: "allowVoiceWithoutDirectDial",
                    label: "Allow voice calls without a published direct dial",
                  },
                ].map((item) => {
                  const val =
                    guardrailToggles[
                      item.key as keyof typeof guardrailToggles
                    ];
                  return (
                    <div
                      key={item.key}
                      className="flex items-center justify-between py-1"
                    >
                      <span className="text-xs text-gray-300 font-medium pr-6">
                        {item.label}
                      </span>
                      <button
                        onClick={() =>
                          setGuardrailToggles((prev) => ({
                            ...prev,
                            [item.key]: !val,
                          }))
                        }
                        className={`w-11 h-6 rounded-full transition-colors relative flex items-center p-0.5 ${
                          val ? "bg-[#00d2aa]" : "bg-gray-700"
                        }`}
                      >
                        <div
                          className={`w-5 h-5 rounded-full bg-white transition-transform ${
                            val ? "translate-x-5" : "translate-x-0"
                          }`}
                        />
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Models Available Section */}
            <div className="bg-[#0b101e] border border-gray-800/80 rounded-xl p-6 shadow-xl space-y-4">
              <div className="border-b border-gray-800 pb-3">
                <h2 className="font-semibold text-white text-sm">
                  Models available
                </h2>
                <p className="text-xs text-gray-400 mt-0.5">
                  Which models agents may route to, and what they cost.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1">
                {[
                  { name: "Haiku 4.5", cost: "$0.25 / 1M tokens", role: "Classification & scheduling" },
                  { name: "Sonnet 5", cost: "$3.00 / 1M tokens", role: "Synthesis & Personalisation" },
                  { name: "Gemini 2.5 Pro", cost: "$1.25 / 1M tokens", role: "Deep research & multimodal" },
                ].map((m) => (
                  <div
                    key={m.name}
                    className="p-3.5 bg-[#070b14] border border-gray-800 rounded-lg"
                  >
                    <div className="font-semibold text-white text-xs">{m.name}</div>
                    <div className="text-[11px] text-[#00d2aa] font-mono mt-1">{m.cost}</div>
                    <div className="text-[10px] text-gray-500 mt-1">{m.role}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* VIEW 8: INBOX */}
        {activeTab === "inbox" && (
          <div className="space-y-6">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white">
                Prospect Inbox
              </h1>
              <p className="text-xs text-gray-400 mt-1">
                Live omnichannel inbound messages and conversational replies across Email, SMS, and LinkedIn.
              </p>
            </div>

            <div className="bg-[#0b101e] border border-gray-800/80 rounded-xl overflow-hidden shadow-xl divide-y divide-gray-800/60">
              {[
                {
                  id: "1",
                  name: "Elena Vasquez",
                  company: "Meridian Data",
                  channel: "email",
                  time: "2h ago",
                  snippet:
                    "Does your platform satisfy SOC 2 Type II compliance and provide us-east-1 data residency guarantees?",
                  status: "Replied by Agent (Pending Approval)",
                  statusColor: "bg-amber-500/10 text-amber-400 border-amber-500/30",
                },
                {
                  id: "2",
                  name: "Jonas Berg",
                  company: "Kestrel Cloud",
                  channel: "linkedin",
                  time: "6h ago",
                  snippet:
                    "Interesting tech. Do you have case studies for high-throughput distributed database sync?",
                  status: "Engaged",
                  statusColor: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
                },
              ].map((msg) => (
                <div
                  key={msg.id}
                  className="p-4 hover:bg-gray-800/30 transition flex items-center justify-between cursor-pointer"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-9 h-9 rounded-full bg-indigo-950 border border-indigo-500/30 text-indigo-300 flex items-center justify-center text-xs font-bold">
                      {msg.name.slice(0, 2).toUpperCase()}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-white text-xs">
                          {msg.name}
                        </span>
                        <span className="text-[11px] text-gray-500">
                          {msg.company}
                        </span>
                        <span className="text-[10px] text-gray-400 bg-gray-800 px-2 py-0.5 rounded border border-gray-700 uppercase">
                          {msg.channel}
                        </span>
                      </div>
                      <p className="text-xs text-gray-300 mt-1 line-clamp-1 max-w-xl">
                        {msg.snippet}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded border font-medium ${msg.statusColor}`}
                    >
                      {msg.status}
                    </span>
                    <span className="text-xs text-gray-500 font-mono">
                      {msg.time}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>

      {/* ================= KILL SWITCH MODAL (Screenshot 4) ================= */}
      {showKillSwitchModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="bg-[#0b101e] border border-red-500/30 rounded-2xl max-w-md w-full p-6 shadow-2xl relative space-y-5 animate-in fade-in zoom-in duration-150">
            {/* Red Warning Header Icon */}
            <div className="w-10 h-10 rounded-lg bg-red-500/10 border border-red-500/30 flex items-center justify-center text-red-500">
              <Power size={20} />
            </div>

            {/* Title & Subtitle */}
            <div>
              <h3 className="text-base font-bold text-white tracking-tight">
                Stop all autonomous activity?
              </h3>
              <p className="text-xs text-gray-400 mt-1.5 leading-relaxed">
                Every campaign stops sending immediately. Nothing is deleted —
                prospects, conversations and history stay exactly as they are.
              </p>
            </div>

            {/* Warning Checklist */}
            <div className="space-y-2.5 pt-1">
              <div className="flex items-start gap-2 text-xs text-gray-300">
                <AlertTriangle size={14} className="text-red-400 shrink-0 mt-0.5" />
                <span>1 campaign stops mid-execution</span>
              </div>
              <div className="flex items-start gap-2 text-xs text-gray-300">
                <AlertTriangle size={14} className="text-red-400 shrink-0 mt-0.5" />
                <span>Queued email, LinkedIn, SMS and voice actions are held</span>
              </div>
              <div className="flex items-start gap-2 text-xs text-gray-300">
                <AlertTriangle size={14} className="text-red-400 shrink-0 mt-0.5" />
                <span>Only an admin can start the platform again</span>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-800">
              <button
                onClick={() => setShowKillSwitchModal(false)}
                className="px-4 py-2 rounded-lg border border-gray-700 bg-gray-800/80 hover:bg-gray-800 text-xs font-medium text-gray-300 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleExecuteKillSwitch}
                className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white text-xs font-bold transition shadow-lg shadow-red-600/30"
              >
                Stop everything
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
