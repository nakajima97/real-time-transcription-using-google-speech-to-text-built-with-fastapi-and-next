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
    print(f"Client connected: {sid}")


@sio.event
async def disconnect(sid):
    """socketioのdisconnectイベント"""
    print(f"Client disconnected: {sid}")
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
    if sid in stream_handlers:
        await stream_handlers[sid].stop_stream()


@sio.on("send_audio_data")
async def handle_audio_input(sid, data):
    """音声データを受信したときのイベントハンドラ"""
    if sid in stream_handlers:
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
        self._stream_id = 0  # ストリームを識別するためのID
        self._cleanup_event = asyncio.Event()  # クリーンアップの完了を追跡

    async def initialize_client(self):
        """SpeechClientの初期化と設定"""
        if not hasattr(self, 'client') or self.client is None:
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

    async def process_queue(self):
        """音声キューを処理する"""
        current_stream_id = self._stream_id
        yield speech.StreamingRecognizeRequest(streaming_config=self.streaming_config)

        while self._is_streaming and self._stream_id == current_stream_id:
            try:
                data = await self.queue.get()
                audio_content = data["audio"]
                yield speech.StreamingRecognizeRequest(audio_content=audio_content)
                self.queue.task_done()
            except Exception as e:
                print(f"Error in process_queue: {e}")
                break

    async def handle_queue(self):
        """音声認識を実行し結果を処理する"""
        current_stream_id = self._stream_id
        try:
            await self.initialize_client()
            stream = await self.client.streaming_recognize(
                requests=self.process_queue()
            )

            async for response in stream:
                # ストリームIDが変更された場合は処理を終了
                if self._stream_id != current_stream_id:
                    break

                if not response.results:
                    continue

                for result in response.results:
                    if not result.alternatives:
                        continue

                    transcription = result.alternatives[0].transcript
                    is_final = result.is_final

                    await sio.emit(
                        "receive_audio_text",
                        {"text": transcription, "isFinal": is_final},
                        room=self.sid,
                    )

                    if is_final:
                        await self.restart_stream()
                        return

        except Exception as e:
            print(f"Error in handle_queue: {e}")
            if self._stream_id == current_stream_id:  # 現在のストリームでエラーが発生した場合のみ再起動
                await self.cleanup_stream()

    async def restart_stream(self):
        """現在のストリームを閉じて新しいストリームを開始する"""
        self._stream_id += 1
        self._cleanup_event.clear()  # イベントをリセット
        await self.cleanup_stream()
        
        if self._is_streaming:
            await self._cleanup_event.wait()  # クリーンアップの完了を待機
            await self.create_new_stream()

    async def cleanup_stream(self):
        """ストリームのリソースを解放する"""
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                self.queue.task_done()
            except asyncio.QueueEmpty:
                break

        self.client = None
        self._cleanup_event.set()  # クリーンアップ完了を通知

    async def create_new_stream(self):
        """新しいストリーミングセッションを作成する"""
        self._is_streaming = True
        await self.initialize_client()
        asyncio.create_task(self.handle_queue())

    async def stop_stream(self):
        """ストリーミングを停止する"""
        print(f"Stopping stream for {self.sid}")
        self._is_streaming = False
        self._cleanup_event.clear()  # イベントをリセット
        await self.queue.put({"audio": b""})
        await self.cleanup_stream()
        await self._cleanup_event.wait()  # クリーンアップの完了を待機