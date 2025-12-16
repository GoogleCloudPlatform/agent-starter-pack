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

import { Content, GenerativeContentBlob, Part } from "@google/generative-ai";
import { EventEmitter } from "eventemitter3";
import { difference } from "lodash";
import {
  isInterrupted,
  isModelTurn,
  isServerContenteMessage,
  isSetupCompleteMessage,
  isToolCallCancellationMessage,
  isToolCallMessage,
  isTurnComplete,
  isAdkEvent,
  isInputTranscription,
  isOutputTranscription,
  LiveIncomingMessage,
  ModelTurn,
  ServerContent,
  StreamingLog,
  ToolCall,
  ToolCallCancellation,
  ToolResponseMessage,
  type LiveConfig,
  type AdkEvent,
} from "../multimodal-live-types";
import { blobToJSON, base64ToArrayBuffer } from "./utils";

/**
 * the events that this client will emit
 */
interface MultimodalLiveClientEventTypes {
  open: () => void;
  log: (log: StreamingLog) => void;
  close: (event: CloseEvent) => void;
  audio: (data: ArrayBuffer) => void;
  content: (data: ServerContent) => void;
  interrupted: () => void;
  setupcomplete: () => void;
  status: (status: string) => void;
  turncomplete: () => void;
  toolcall: (toolCall: ToolCall) => void;
  toolcallcancellation: (toolcallCancellation: ToolCallCancellation) => void;
  // ADK events
  inputtranscription: (text: string) => void;
  outputtranscription: (text: string) => void;
  adkevent: (event: AdkEvent) => void;
}

export type MultimodalLiveAPIClientConnection = {
  url?: string;
  runId?: string;
  userId?: string;
};

/**
 * A event-emitting class that manages the connection to the websocket and emits
 * events to the rest of the application.
 * If you dont want to use react you can still use this.
 */
export class MultimodalLiveClient extends EventEmitter<MultimodalLiveClientEventTypes> {
  public ws: WebSocket | null = null;
  protected config: LiveConfig | null = null;
  public url: string = "";
  private runId: string;
  private userId?: string;
  private firstContentSent: boolean = false;
  private audioChunksSent: number = 0;
  private lastAudioSendTime: number = 0;
  private readonly INITIAL_SEND_INTERVAL_MS = 300; // Start slow: 300ms between chunks
  private readonly NORMAL_SEND_INTERVAL_MS = 125; // Normal rate: 125ms (8 chunks/sec)
  private readonly RAMPUP_CHUNKS = 10; // Number of chunks to send at reduced rate

  constructor({ url, userId, runId }: MultimodalLiveAPIClientConnection) {
    super();
    const defaultWsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`;
    url = url || defaultWsUrl;
    this.url = new URL("ws", url).href;
    this.userId = userId;
    this.runId = runId || crypto.randomUUID(); // Ensure runId is always a string by providing default
    this.send = this.send.bind(this);
  }

  get currentRunId(): string {
    return this.runId;
  }

  log(type: string, message: StreamingLog["message"]) {
    const log: StreamingLog = {
      date: new Date(),
      type,
      message,
    };
    this.emit("log", log);
  }

  connect(newRunId?: string): Promise<boolean> {
    const ws = new WebSocket(this.url);

    // Update runId if provided
    if (newRunId) {
      this.runId = newRunId;
    }

    // Reset connection state
    this.firstContentSent = false;
    this.audioChunksSent = 0;
    this.lastAudioSendTime = 0;

    ws.addEventListener("message", async (evt: MessageEvent) => {
      if (evt.data instanceof Blob) {
        this.receive(evt.data);
      } else if (typeof evt.data === "string") {
        try {
          const jsonData = JSON.parse(evt.data);
          
          // Handle different message types from backend
          if (jsonData.setupComplete) {
            this.emit("setupcomplete");
            this.log("server.setupComplete", "Session ready");
          } else if (jsonData.serverContent) {
            // Handle serverContent messages
            this.receive(new Blob([JSON.stringify(jsonData)], {type: 'application/json'}));
          } else if (jsonData.toolCall) {
            // Handle tool calls
            this.receive(new Blob([JSON.stringify(jsonData)], {type: 'application/json'}));
          } else if (jsonData.status) {
            this.log("server.status", jsonData.status);
            console.log("Status:", jsonData.status);
          } else if (jsonData.error) {
            this.log("server.error", jsonData.error);
            console.error("Server error:", jsonData.error);
          } else {
            // Try to process as a regular message
            this.receive(new Blob([JSON.stringify(jsonData)], {type: 'application/json'}));
          }
        } catch (error) {
          console.error("Error parsing message:", error);
        }
      } else {
        console.log("Unhandled message type:", evt);
      }
    });

    return new Promise((resolve, reject) => {
      const onError = (ev: Event) => {
        this.disconnect(ws);
        const message = `Could not connect to "${this.url}"`;
        this.log(`server.${ev.type}`, message);
        reject(new Error(message));
      };
      ws.addEventListener("error", onError);
      ws.addEventListener("open", (ev: Event) => {
        this.log(`client.${ev.type}`, `connected to socket`);
        this.emit("open");

        this.ws = ws;
        // Send initial setup message with user_id for backend
        const setupMessage = {
          user_id: this.userId || "default_user",
          setup: {
            run_id: this.runId,
            user_id: this.userId || "default_user",
          },
        };
        this._sendDirect(setupMessage);
        ws.removeEventListener("error", onError);
        ws.addEventListener("close", (ev: CloseEvent) => {
          console.log(ev);
          this.disconnect(ws);
          let reason = ev.reason || "";
          if (reason.toLowerCase().includes("error")) {
            const prelude = "ERROR]";
            const preludeIndex = reason.indexOf(prelude);
            if (preludeIndex > 0) {
              reason = reason.slice(
                preludeIndex + prelude.length + 1,
                Infinity,
              );
            }
          }
          this.log(
            `server.${ev.type}`,
            `disconnected ${reason ? `with reason: ${reason}` : ``}`,
          );
          this.emit("close", ev);
        });
        resolve(true);
      });
    });
  }

  disconnect(ws?: WebSocket) {
    // could be that this is an old websocket and there's already a new instance
    // only close it if its still the correct reference
    if ((!ws || this.ws === ws) && this.ws) {
      this.ws.close();
      this.ws = null;
      this.log("client.close", `Disconnected`);
      return true;
    }
    return false;
  }
  protected async receive(blob: Blob) {
    const response = (await blobToJSON(blob)) as LiveIncomingMessage;
    console.log("Parsed response:", response);

    if (isToolCallMessage(response)) {
      this.log("server.toolCall", response);
      this.emit("toolcall", response.toolCall);
      return;
    }
    if (isToolCallCancellationMessage(response)) {
      this.log("receive.toolCallCancellation", response);
      this.emit("toolcallcancellation", response.toolCallCancellation);
      return;
    }

    if (isSetupCompleteMessage(response)) {
      this.log("server.send", "setupComplete");
      this.emit("setupcomplete");
      return;
    }

    // this json also might be `contentUpdate { interrupted: true }`
    // or contentUpdate { end_of_turn: true }
    if (isServerContenteMessage(response)) {
      const { serverContent } = response;
      if (isInterrupted(serverContent)) {
        this.log("receive.serverContent", "interrupted");
        this.emit("interrupted");
        return;
      }
      if (isTurnComplete(serverContent)) {
        this.log("server.send", "turnComplete");
        this.emit("turncomplete");
        //plausible there's more to the message, continue
      }

      if (isModelTurn(serverContent)) {
        let parts: Part[] = serverContent.modelTurn.parts;

        // when its audio that is returned for modelTurn (check both camelCase and snake_case)
        const audioParts = parts.filter(
          (p: any) => {
            const inlineData = p.inlineData || p.inline_data;
            const mimeType = inlineData?.mimeType || inlineData?.mime_type;
            return inlineData && mimeType && mimeType.startsWith("audio/pcm");
          }
        );
        const base64s = audioParts.map((p: any) => {
          const inlineData = p.inlineData || p.inline_data;
          return inlineData?.data;
        });

        // strip the audio parts out of the modelTurn
        const otherParts = difference(parts, audioParts);
        // console.log("otherParts", otherParts);

        base64s.forEach((b64) => {
          if (b64) {
            const data = base64ToArrayBuffer(b64);
            this.emit("audio", data);
            this.log(`server.audio`, `buffer (${data.byteLength})`);
          }
        });
        if (!otherParts.length) {
          return;
        }

        parts = otherParts;

        const content: ModelTurn = { modelTurn: { parts } };
        this.emit("content", content);
        this.log(`server.content`, response);
      }
    } else if (isAdkEvent(response)) {
      // Handle ADK events
      this.emit("adkevent", response);

      // Handle specific ADK event types
      if (isInputTranscription(response)) {
        this.emit("inputtranscription", response.input_transcription!.text);
      }

      if (isOutputTranscription(response)) {
        this.emit("outputtranscription", response.output_transcription!.text);
      }

      // Handle ADK content (text responses from agent)
      if (response.content && response.content.parts) {
        const parts = response.content.parts;

        // Extract function calls for tool call logging
        const functionCallParts = parts.filter((p: any) => p.function_call);

        // Log function calls as tool calls for the console
        if (functionCallParts.length > 0) {
          const functionCalls = functionCallParts.map((p: any) => ({
            id: p.function_call.id,
            name: p.function_call.name,
            args: p.function_call.args || {}
          }));

          const toolCallMessage = {
            toolCall: {
              functionCalls: functionCalls
            }
          };

          this.log("server.toolCall", toolCallMessage);
          this.emit("toolcall", toolCallMessage.toolCall);
        }
        
        // Extract audio parts for playing (check both camelCase and snake_case)
        const audioParts = parts.filter(
          (p: any) => {
            const inlineData = p.inlineData || p.inline_data;
            const mimeType = inlineData?.mimeType || inlineData?.mime_type;
            return inlineData && mimeType && mimeType.startsWith("audio/");
          }
        );
        
        // Play audio if present
        audioParts.forEach((audioPart: any) => {
          const inlineData = audioPart.inlineData || audioPart.inline_data;
          if (inlineData && inlineData.data) {
            const audioData = base64ToArrayBuffer(inlineData.data);
            
            // Only emit audio if we have a valid buffer with data
            if (audioData.byteLength > 0) {
              this.emit("audio", audioData);
              this.log(`server.audio`, `buffer (${audioData.byteLength}) - ${inlineData.mime_type || inlineData.mimeType}`);
            } else {
              this.log(`server.audio`, `invalid audio buffer - skipped`);
            }
          }
        });
        
        // Send content for other parts (text, etc.) - exclude function calls and audio
        const nonAudioNonFunctionParts = parts.filter(
          (p: any) => {
            const inlineData = p.inlineData || p.inline_data;
            const mimeType = inlineData?.mimeType || inlineData?.mime_type;
            const hasAudio = inlineData && mimeType && mimeType.startsWith("audio/");
            const hasFunctionCall = p.function_call;
            return !hasAudio && !hasFunctionCall;
          }
        );
        
        if (nonAudioNonFunctionParts.length > 0) {
          const content: ModelTurn = { modelTurn: { parts: nonAudioNonFunctionParts } };
          this.emit("content", content);
          this.log("server.content", `content with ${nonAudioNonFunctionParts.length} non-audio, non-function parts`);
        }
      }
      
      // Handle turn complete
      if (response.turn_complete) {
        this.emit("turncomplete");
        this.log("server.turncomplete", "ADK turn complete");
      }
      
      // Handle interruption
      if (response.interrupted) {
        this.emit("interrupted");
        this.log("server.interrupted", "ADK interrupted");
      }
    } else {
      // Ignore webpack dev server HMR messages
      const hmrTypes = ["liveReload", "reconnect", "overlay", "hash", "ok", "warnings", "errors", "invalid", "still-ok", "hot"];
      if (typeof (response as any).type === "string" && hmrTypes.includes((response as any).type)) {
        return;
      }
      console.log("received unmatched message", response);
      this.log("received unmatched message", response);
    }
  }

  /**
   * send realtimeInput, this is base64 chunks of "audio/pcm" and/or "image/jpg"
   */
  sendRealtimeInput(chunks: GenerativeContentBlob[]) {
    // Don't send if WebSocket is not open - this prevents flooding the queue
    // during connection setup
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return;
    }

    let hasAudio = false;
    let hasVideo = false;
    for (let i = 0; i < chunks.length; i++) {
      const ch = chunks[i];
      if (ch.mimeType.includes("audio")) {
        hasAudio = true;
      }
      if (ch.mimeType.includes("image")) {
        hasVideo = true;
      }
      if (hasAudio && hasVideo) {
        break;
      }
    }

    // Throttle audio chunks during initial connection phase
    if (hasAudio && !hasVideo) {
      const now = Date.now();

      // Calculate required interval based on how many chunks we've sent
      const requiredInterval = this.audioChunksSent < this.RAMPUP_CHUNKS
        ? this.INITIAL_SEND_INTERVAL_MS
        : this.NORMAL_SEND_INTERVAL_MS;

      // If not enough time has passed since last send, drop this chunk
      if (this.lastAudioSendTime > 0 && (now - this.lastAudioSendTime) < requiredInterval) {
        return;
      }

      this.lastAudioSendTime = now;
      this.audioChunksSent++;
    }

    const message =
      hasAudio && hasVideo
        ? "audio + video"
        : hasAudio
          ? "audio"
          : hasVideo
            ? "video"
            : "unknown";

    // Convert to LiveRequest format for backend
    for (const chunk of chunks) {
      let data: any = {
        blob: {
          mimeType: chunk.mimeType,
          data: chunk.data,
        },
      };

      // For remote mode: wrap first content in {user_id, live_request} format
      if (!this.firstContentSent) {
        data = {
          user_id: this.userId || "default_user",
          live_request: data,
        };
        this.firstContentSent = true;
      }

      this._sendDirect(data);
    }
    this.log(`client.realtimeInput`, message);
  }

  /**
   *  send a response to a function call and provide the id of the functions you are responding to
   */
  sendToolResponse(toolResponse: ToolResponseMessage["toolResponse"]) {
    const message: ToolResponseMessage = {
      toolResponse,
    };

    this._sendDirect(message);
    this.log(`client.toolResponse`, message);
  }

  /**
   * send normal content parts such as { text }
   */
  send(parts: Part | Part[], _turnComplete: boolean = true) {
    parts = Array.isArray(parts) ? parts : [parts];
    const content: Content = {
      role: "user",
      parts,
    };

    // Convert to LiveRequest format for backend
    let data: any = {
      content: content,
    };

    // For remote mode: wrap first content in {user_id, live_request} format
    if (!this.firstContentSent) {
      data = {
        user_id: this.userId || "default_user",
        live_request: data,
      };
      this.firstContentSent = true;
    }

    this._sendDirect(data);
    this.log(`client.send`, `content with ${parts.length} parts`);
  }

  /**
   *  used internally to send all messages
   *  don't use directly unless trying to send an unsupported message type
   */
  _sendDirect(request: object) {
    if (!this.ws) {
      throw new Error("WebSocket is not connected");
    }
    const str = JSON.stringify(request);
    this.ws.send(str);
  }
}
