# AgentForge Frontend

Next.js-based frontend for the AgentForge multi-agent platform.

## Features

- Real-time chat interface with WebSocket communication
- Dark theme optimized UI
- Auto-reconnection with exponential backoff
- Typing indicators and message animations
- Responsive design with Tailwind CSS

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
npm install
```

### Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Build

```bash
npm run build
npm start
```

## Project Structure

```
frontend/
├── app/
│   ├── components/
│   │   ├── ChatWindow.tsx      # Main chat interface
│   │   └── MessageBubble.tsx   # Individual message display
│   ├── globals.css             # Global styles
│   ├── layout.tsx              # Root layout
│   └── page.tsx                # Home page
├── lib/
│   └── websocket.ts            # WebSocket client utility
└── public/                     # Static assets
```

## Configuration

The frontend connects to the backend WebSocket at `ws://localhost:8000/api/v1/ws/chat/{conversationId}`.

To change the backend URL, modify the `wsUrl` in `app/components/ChatWindow.tsx`.

## Technologies

- Next.js 14 (App Router)
- React 18
- TypeScript
- Tailwind CSS
- WebSocket API
