"use client";

import Image from "next/image";
import { useState, useRef, useEffect } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Loader2, Mic, Upload, Info } from "lucide-react";

export default function Home() {
  // State for API key and mode
  const [apiKey, setApiKey] = useState(process.env.NEXT_PUBLIC_API_KEY || "");
  const [useApi, setUseApi] = useState(true);
  const [showTimestamps, setShowTimestamps] = useState(true);
  const [device, setDevice] = useState("auto");

  // State for file upload
  const [file, setFile] = useState<File | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);

  // State for recording
  const [isRecording, setIsRecording] = useState(false);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [recordedUrl, setRecordedUrl] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  // State for transcription
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [transcription, setTranscription] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  // Handle file upload
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      setFile(selectedFile);
      setAudioUrl(URL.createObjectURL(selectedFile));
      setError(null);
    }
  };

  // Start recording
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, {
          type: "audio/wav",
        });
        setRecordedBlob(audioBlob);
        const audioUrl = URL.createObjectURL(audioBlob);
        setRecordedUrl(audioUrl);
      };

      mediaRecorder.start();
      setIsRecording(true);
      setError(null);
    } catch (err) {
      console.error("Error accessing microphone:", err);
      setError(
        "Error accessing microphone. Please make sure your browser has permission to use the microphone."
      );
    }
  };

  // Stop recording
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);

      // Stop all audio tracks
      if (mediaRecorderRef.current.stream) {
        mediaRecorderRef.current.stream
          .getTracks()
          .forEach((track) => track.stop());
      }
    }
  };

  // Transcribe audio
  const transcribeAudio = async (audioBlob: Blob) => {
    setIsTranscribing(true);
    setError(null);
    setTranscription(null);

    try {
      const formData = new FormData();
      formData.append("file", audioBlob, "audio.wav");
      formData.append("api_key", apiKey);
      formData.append("use_api", useApi.toString());
      formData.append("with_timestamps", showTimestamps.toString());
      formData.append("device", device);

      const response = await fetch("http://localhost:8000/transcribe", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to transcribe audio");
      }

      const result = await response.json();
      setTranscription(result);
    } catch (err) {
      console.error("Error transcribing audio:", err);
      setError(
        err instanceof Error ? err.message : "An unknown error occurred"
      );
    } finally {
      setIsTranscribing(false);
    }
  };

  // Render timestamps visualization
  const renderTimestamps = () => {
    if (
      !transcription ||
      !transcription.timestamps ||
      transcription.timestamps.length === 0
    ) {
      return null;
    }

    return (
      <div className="mt-4 p-4 bg-muted rounded-md">
        <h3 className="text-lg font-medium mb-2">Word Timestamps</h3>
        <div className="space-y-1">
          {transcription.timestamps.map((ts: any, index: number) => (
            <div key={index} className="p-2 bg-background rounded-sm text-sm">
              [{ts.start.toFixed(2)}s - {ts.end.toFixed(2)}s] {ts.word}
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="flex flex-col items-center mb-8">
        <h1 className="text-4xl font-bold text-primary mb-2">
          Typhoon ASR Demo
        </h1>
        <p className="text-xl text-muted-foreground">
          Thai Speech Recognition in Real-time
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Sidebar */}
        <Card className="">
          <CardHeader>
            <CardTitle>Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="mode">Transcription Mode</Label>
                <Switch
                  id="mode"
                  checked={useApi}
                  onCheckedChange={setUseApi}
                />
              </div>
              <p className="text-sm text-muted-foreground">
                {useApi ? "API Mode (Cloud)" : "Local Mode (Self-hosted)"}
              </p>
            </div>

            {useApi && (
              <div className="space-y-2">
                <Label htmlFor="apiKey">API Key</Label>
                <Input
                  id="apiKey"
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="Enter your Typhoon API key"
                />
              </div>
            )}

            {!useApi && (
              <div className="space-y-2">
                <Label htmlFor="device">Device</Label>
                <select
                  id="device"
                  className="w-full p-2 border rounded-md"
                  value={device}
                  onChange={(e) => setDevice(e.target.value)}
                >
                  <option value="auto">Auto</option>
                  <option value="cpu">CPU</option>
                  <option value="cuda">CUDA (GPU)</option>
                </select>
              </div>
            )}

            <div className="flex items-center space-x-2">
              <Switch
                id="timestamps"
                checked={showTimestamps}
                onCheckedChange={setShowTimestamps}
              />
              <Label htmlFor="timestamps">Show Word Timestamps</Label>
            </div>
          </CardContent>
        </Card>

        {/* Main content */}
        <div className="md:col-span-2 space-y-6">
          <Tabs defaultValue="upload">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="upload">Upload Audio</TabsTrigger>
              <TabsTrigger value="record">Record Audio</TabsTrigger>
            </TabsList>

            {/* Upload Tab */}
            <TabsContent value="upload" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Upload an audio file</CardTitle>
                  <CardDescription>
                    Supported formats: .wav, .mp3, .flac, .ogg, .opus
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-center w-full">
                    <label
                      htmlFor="dropzone-file"
                      className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer bg-muted/50 hover:bg-muted"
                    >
                      <div className="flex flex-col items-center justify-center pt-5 pb-6">
                        <Upload className="w-10 h-10 mb-3 text-muted-foreground" />
                        <p className="mb-2 text-sm text-muted-foreground">
                          <span className="font-semibold">Click to upload</span>{" "}
                          or drag and drop
                        </p>
                        <p className="text-xs text-muted-foreground">
                          WAV, MP3, FLAC, OGG or OPUS
                        </p>
                      </div>
                      <input
                        id="dropzone-file"
                        type="file"
                        className="hidden"
                        accept=".wav,.mp3,.flac,.ogg,.opus"
                        onChange={handleFileChange}
                      />
                    </label>
                  </div>

                  {file && (
                    <div className="mt-4">
                      <p className="text-sm font-medium">
                        Selected file: {file.name}
                      </p>
                      {audioUrl && (
                        <audio
                          className="w-full mt-2"
                          controls
                          src={audioUrl}
                        ></audio>
                      )}
                    </div>
                  )}
                </CardContent>
                <CardFooter>
                  <Button
                    onClick={() => file && transcribeAudio(file)}
                    disabled={!file || isTranscribing}
                    className="w-full"
                  >
                    {isTranscribing ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Transcribing...
                      </>
                    ) : (
                      "Transcribe"
                    )}
                  </Button>
                </CardFooter>
              </Card>
            </TabsContent>

            {/* Record Tab */}
            <TabsContent value="record" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Record audio from your microphone</CardTitle>
                  <CardDescription>
                    Click the button below to start recording
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex flex-col items-center justify-center">
                  <div className="mb-4">
                    {isRecording ? (
                      <div className="p-6 rounded-full bg-red-100 animate-pulse">
                        <Mic className="h-12 w-12 text-red-500" />
                      </div>
                    ) : (
                      <div className="p-6 rounded-full bg-muted">
                        <Mic className="h-12 w-12 text-muted-foreground" />
                      </div>
                    )}
                  </div>

                  <div className="flex space-x-2">
                    {!isRecording ? (
                      <Button onClick={startRecording} variant="outline">
                        Start Recording
                      </Button>
                    ) : (
                      <Button onClick={stopRecording} variant="destructive">
                        Stop Recording
                      </Button>
                    )}
                  </div>

                  {recordedUrl && (
                    <div className="mt-4 w-full">
                      <p className="text-sm font-medium mb-2">
                        Recorded audio:
                      </p>
                      <audio
                        className="w-full"
                        controls
                        src={recordedUrl}
                      ></audio>
                    </div>
                  )}
                </CardContent>
                <CardFooter>
                  <Button
                    onClick={() =>
                      recordedBlob && transcribeAudio(recordedBlob)
                    }
                    disabled={!recordedBlob || isTranscribing}
                    className="w-full"
                  >
                    {isTranscribing ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Transcribing...
                      </>
                    ) : (
                      "Transcribe Recording"
                    )}
                  </Button>
                </CardFooter>
              </Card>
            </TabsContent>
          </Tabs>

          {/* Results */}
          {error && (
            <Alert variant="destructive">
              <AlertTitle>Error</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {transcription && (
            <Card>
              <CardHeader>
                <CardTitle>Transcription Results</CardTitle>
              </CardHeader>
              <CardContent>
                <Textarea
                  className="min-h-[100px] text-lg"
                  readOnly
                  value={transcription.text}
                />

                <div className="grid grid-cols-2 gap-4 mt-4">
                  <div className="p-4 bg-muted rounded-md">
                    <p className="text-sm font-medium">Processing Time</p>
                    <p className="text-2xl">
                      {transcription.processing_time?.toFixed(2)}s
                    </p>
                  </div>

                  {transcription.audio_duration && (
                    <div className="p-4 bg-muted rounded-md">
                      <p className="text-sm font-medium">Audio Duration</p>
                      <p className="text-2xl">
                        {transcription.audio_duration.toFixed(2)}s
                      </p>
                    </div>
                  )}
                </div>

                {showTimestamps && renderTimestamps()}
              </CardContent>
            </Card>
          )}
        </div>

        {/* About */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Info className="h-5 w-5 mr-2" />
              About Typhoon ASR
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="mb-2">
              This demo uses{" "}
              <a
                href="https://opentyphoon.ai/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary underline"
              >
                Typhoon ASR
              </a>{" "}
              for Thai speech recognition.
            </p>

            <h3 className="font-medium mt-4 mb-2">Supported audio formats:</h3>
            <ul className="list-disc pl-5 space-y-1">
              <li>.wav</li>
              <li>.mp3</li>
              <li>.flac</li>
              <li>.ogg</li>
              <li>.opus</li>
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
