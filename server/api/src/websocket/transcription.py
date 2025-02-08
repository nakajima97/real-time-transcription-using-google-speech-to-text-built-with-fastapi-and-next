import socketio
from google.cloud import speech
import asyncio

# Setup socket.io
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins=[])
app_socketio = socketio.ASGIApp(sio)

# アクティブなストリームハンドラを保持
stream_handlers = {}


@sio.event
async def connect(sid, environ):
    """socketioのconnectイベント"""
    print("connect ", sid)


@sio.event
async def disconnect(sid):
    """socketioのdisconnectイベント"""
    print(f"disconnect {sid}")
    if sid in stream_handlers:
        await stream_handlers[sid].stop_stream()
        del stream_handlers[sid]


@sio.on("start_google_cloud_stream")
async def start_stream(sid):
    """音声ストリームを開始する"""
    print(f"Starting recognition for {sid}")
    if sid not in stream_handlers:
        stream_handlers[sid] = AudioStreamHandler(sid)
    await stream_handlers[sid].create_new_stream()


@sio.on("stop_google_cloud_stream")
async def stop_stream(sid):
    """音声ストリームを停止する"""
    print(f"Stopping recognition for {sid}")
    if sid in stream_handlers:
        await stream_handlers[sid].stop_stream()


@sio.on("send_audio_data")
async def handle_audio_input(sid, data):
    """音声データを受信したときのイベントハンドラ"""
    if sid in stream_handlers:
        print(f"[AUDIO] Received audio data for session {sid}")
        await stream_handlers[sid].queue.put(data)


class AudioStreamHandler:
    """音声ストリームを処理するクラス"""

    def __init__(self, sid):
        """
        AudioStreamHandlerを初期化する

        Args:
            sid: セッションID
        """
        self.sid = sid
        self.queue = asyncio.Queue()
        self._is_streaming = False
        self.last_message_final = False
        self._current_task = None
        self._stream_id = 0  # ストリームを識別するためのID
        self._cleanup_event = asyncio.Event()  # クリーンアップの完了を追跡
        print(f"[INIT] Created new AudioStreamHandler for session {sid}")

    async def initialize_client(self):
        """SpeechClientの初期化と設定"""
        if not hasattr(self, 'client') or self.client is None:
            print(f"[CLIENT] Initializing new SpeechClient for session {self.sid}")
            self.client = speech.SpeechAsyncClient()
            self.streaming_config = speech.StreamingRecognitionConfig(
                config=speech.RecognitionConfig(
                    encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                    sample_rate_hertz=16000,
                    language_code='ja-JP',
                    enable_automatic_punctuation=True,
                ),
                interim_results=True,
            )
            print(f"[CLIENT] SpeechClient initialized for session {self.sid}")
        else:
            print(f"[CLIENT] Using existing SpeechClient for session {self.sid}")

    async def process_queue(self):
        """音声キューを処理する"""
        current_stream_id = self._stream_id
        yield speech.StreamingRecognizeRequest(streaming_config=self.streaming_config)
        print(f"[QUEUE] Starting queue processing for session {self.sid} (stream {current_stream_id})")

        while self._is_streaming and self._stream_id == current_stream_id:
            try:
                data = await self.queue.get()
                audio_content = data["audio"]
                yield speech.StreamingRecognizeRequest(audio_content=audio_content)
                self.queue.task_done()
            except Exception as e:
                print(f"[ERROR] Error in process_queue for session {self.sid}: {e}")
                break

        print(f"[QUEUE] Queue processing stopped for session {self.sid} (stream {current_stream_id})")

    async def handle_queue(self):
        """音声認識を実行し結果を処理する"""
        current_stream_id = self._stream_id
        try:
            print(f"[STREAM] Starting stream handling for session {self.sid} (stream {current_stream_id})")
            await self.initialize_client()
            stream = await self.client.streaming_recognize(
                requests=self.process_queue()
            )
            print(f"[STREAM] Stream created successfully for session {self.sid} (stream {current_stream_id})")

            async for response in stream:
                # ストリームIDが変更された場合は処理を終了
                if self._stream_id != current_stream_id:
                    print(f"[STREAM] Stream {current_stream_id} is obsolete, stopping")
                    break

                if not response.results:
                    continue

                for result in response.results:
                    if not result.alternatives:
                        continue

                    transcription = result.alternatives[0].transcript
                    is_final = result.is_final
                    print(f"[TRANSCRIPTION] {self.sid}: {'FINAL' if is_final else 'INTERIM'} - {transcription}")

                    await sio.emit(
                        "receive_audio_text",
                        {"text": transcription, "isFinal": is_final},
                        room=self.sid,
                    )

                    if is_final:
                        print(f"[STREAM] Final result received for session {self.sid} (stream {current_stream_id})")
                        await self.restart_stream()
                        return

        except Exception as e:
            print(f"[ERROR] Error in handle_queue for session {self.sid}: {e}")
            if self._stream_id == current_stream_id:  # 現在のストリームでエラーが発生した場合のみ再起動
                await self.cleanup_stream()
        finally:
            print(f"[STREAM] Stream handling finished for session {self.sid} (stream {current_stream_id})")

    async def restart_stream(self):
        """現在のストリームを閉じて新しいストリームを開始する"""
        print(f"[RESTART] Beginning stream restart for session {self.sid}")
        self._stream_id += 1
        self._cleanup_event.clear()  # イベントをリセット
        await self.cleanup_stream()
        
        if self._is_streaming:
            print(f"[RESTART] Stream is still active, waiting for cleanup to complete for session {self.sid}")
            await self._cleanup_event.wait()  # クリーンアップの完了を待機
            print(f"[RESTART] Cleanup confirmed, creating new stream for session {self.sid}")
            await self.create_new_stream()

    async def cleanup_stream(self):
        """ストリームのリソースを解放する"""
        print(f"[CLEANUP] Starting cleanup for session {self.sid}")
        
        # 現在のキューをクリア
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                self.queue.task_done()
            except asyncio.QueueEmpty:
                break

        if hasattr(self, 'client') and self.client is not None:
            print(f"[CLEANUP] Closing client for session {self.sid}")
            self.client = None
        
        self.last_message_final = False
        self._cleanup_event.set()  # クリーンアップ完了を通知
        print(f"[CLEANUP] Cleanup completed for session {self.sid}")

    async def create_new_stream(self):
        """新しいストリーミングセッションを作成する"""
        print(f"[CREATE] Creating new stream for session {self.sid}")
        self._is_streaming = True
        await self.initialize_client()
        asyncio.create_task(self.handle_queue())
        print(f"[CREATE] New stream created and started for session {self.sid}")

    async def stop_stream(self):
        """ストリーミングを停止する"""
        print(f"[STOP] Stopping stream for session {self.sid}")
        self._is_streaming = False
        self._cleanup_event.clear()  # イベントをリセット
        await self.queue.put({"audio": b""})
        await self.cleanup_stream()
        await self._cleanup_event.wait()  # クリーンアップの完了を待機
        print(f"[STOP] Stream stopped for session {self.sid}")