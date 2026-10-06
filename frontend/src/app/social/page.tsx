"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { SocialCommandCenter } from "@/components/social/SocialCommandCenter";
export default function SocialPage(){const router=useRouter();const {isAuthenticated,isRestoring}=useAuth();useEffect(()=>{if(!isRestoring&&!isAuthenticated)router.replace("/auth")},[isAuthenticated,isRestoring,router]);if(isRestoring||!isAuthenticated)return <main style={{minHeight:"100vh",display:"grid",placeItems:"center",background:"#04040D",color:"#62628A",fontFamily:"monospace",fontSize:12}}>RESTORING SECURE SESSION…</main>;return <SocialCommandCenter/>;}
