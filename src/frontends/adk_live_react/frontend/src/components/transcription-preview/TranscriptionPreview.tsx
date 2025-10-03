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

import { useEffect, useRef, useState } from "react";
import { useLiveAPIContext } from "../../contexts/LiveAPIContext";
import cn from "classnames";
import "./transcription-preview.scss";

export type TranscriptionPreviewProps = {
  open: boolean;
};

export default function TranscriptionPreview({ open }: TranscriptionPreviewProps) {
  const { client } = useLiveAPIContext();
  const [inputTexts, setInputTexts] = useState<string[]>([]);
  const [outputTexts, setOutputTexts] = useState<string[]>([]);
  const inputRef = useRef<HTMLDivElement>(null);
  const outputRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleInputTranscription = (text: string) => {
      setInputTexts((prev) => [...prev, text]);
      // Auto-scroll to bottom
      setTimeout(() => {
        if (inputRef.current) {
          inputRef.current.scrollTop = inputRef.current.scrollHeight;
        }
      }, 0);
    };

    const handleOutputTranscription = (text: string) => {
      setOutputTexts((prev) => [...prev, text]);
      // Auto-scroll to bottom
      setTimeout(() => {
        if (outputRef.current) {
          outputRef.current.scrollTop = outputRef.current.scrollHeight;
        }
      }, 0);
    };

    client.on("inputtranscription", handleInputTranscription);
    client.on("outputtranscription", handleOutputTranscription);

    return () => {
      client.off("inputtranscription", handleInputTranscription);
      client.off("outputtranscription", handleOutputTranscription);
    };
  }, [client]);

  return (
    <div className={cn("transcription-preview", { open })}>
      <div className="transcription-section input-section">
        <div className="transcription-header">
          <span className="material-symbols-outlined">mic</span>
          <h3>Input</h3>
        </div>
        <div className="transcription-content" ref={inputRef}>
          {inputTexts.length > 0 ? (
            <>
              {inputTexts.map((text, index) => (
                <p key={index} className={index === inputTexts.length - 1 ? "current" : "previous"}>
                  {text}
                </p>
              ))}
            </>
          ) : (
            <p className="placeholder">Listening...</p>
          )}
        </div>
      </div>

      <div className="transcription-section output-section">
        <div className="transcription-header">
          <span className="material-symbols-outlined">volume_up</span>
          <h3>Output</h3>
        </div>
        <div className="transcription-content" ref={outputRef}>
          {outputTexts.length > 0 ? (
            <>
              {outputTexts.map((text, index) => (
                <p key={index} className={index === outputTexts.length - 1 ? "current" : "previous"}>
                  {text}
                </p>
              ))}
            </>
          ) : (
            <p className="placeholder">Waiting for response...</p>
          )}
        </div>
      </div>
    </div>
  );
}
