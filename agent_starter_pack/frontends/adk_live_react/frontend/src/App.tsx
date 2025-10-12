/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { useRef, useState } from "react";
import "./App.scss";
import { LiveAPIProvider } from "./contexts/LiveAPIContext";
import SidePanel from "./components/side-panel/SidePanel";
import cn from "classnames";

// In development mode (frontend on :8501), connect to backend on :8000
const isDevelopment = window.location.port === '8501';
const defaultHost = isDevelopment ? `${window.location.hostname}:8000` : window.location.host;
const defaultUri = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${defaultHost}/`;

function App() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videoStream, setVideoStream] = useState<MediaStream | null>(null);
  const [serverUrl, setServerUrl] = useState<string>(defaultUri);
  const [userId, setUserId] = useState<string>("user1");

  return (
    <div className="App">
      <LiveAPIProvider url={serverUrl} userId={userId}>
        <div className="streaming-console">
          <SidePanel
            videoRef={videoRef}
            supportsVideo={true}
            onVideoStreamChange={setVideoStream}
            serverUrl={serverUrl}
            userId={userId}
            onServerUrlChange={setServerUrl}
            onUserIdChange={setUserId}
          />
          <main>
            <div className="main-app-area">
              <video
                className={cn("stream", {
                  hidden: !videoRef.current || !videoStream,
                })}
                ref={videoRef}
                autoPlay
                playsInline
              />
            </div>
          </main>
        </div>
      </LiveAPIProvider>
    </div>
  );
}

export default App;
