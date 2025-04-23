'use client'

import { useEffect } from 'react'
import '@/app/globals.css'
import {getApiBaseUrl} from "@/lib/api-config";

export default function RasaChatWidget() {
  useEffect(() => {
    const script = document.createElement('script')
    script.src = 'https://cdn.jsdelivr.net/npm/rasa-webchat/lib/index.min.js'
    script.async = true
    script.onload = () => {
      window.WebChat.default(
        {
          initPayload: '/greet',
          customData: { language: 'en' }, // arbitrary custom data
          socketUrl: getApiBaseUrl(), // your MCP server with WebSocket support
          title: 'The Movie Master 🎬',
          subtitle: 'Ask me anything about movies!',
          inputTextFieldHint: 'Type your message...',
          showCloseButton: true,
          profileAvatar: '/bot_avatar.png',
          showFullScreenButton: true,
          params: {
            storage: 'session'
          }
        },
        null
      )
    }
    document.body.appendChild(script)
  }, [])

  return null
}
