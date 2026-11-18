import React from 'react'
import ReactDOM from 'react-dom/client'
import { AgentStreamingTerminal } from './day19_frontend_generative_ui'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <div className="py-12 px-4">
      <AgentStreamingTerminal />
    </div>
  </React.StrictMode>
)
