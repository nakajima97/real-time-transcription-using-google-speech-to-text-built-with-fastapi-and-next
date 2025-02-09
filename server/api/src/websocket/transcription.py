import socketio
from google.cloud import speech_v2
import asyncio
import logging
from src.settings.env import get_env_value

# Setup socket.io
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins=[])
app_socketio = socketio.ASGIApp(sio)

# アクティブなストリームハンドラを保持
stream_handlers = {}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
            self.client = speech_v2.SpeechAsyncClient()
            self.streaming_config = speech_v2.types.StreamingRecognitionConfig(
                config=speech_v2.types.RecognitionConfig(
                    # 自動で音声を解析する設定があるが、対応していないエンコーディングを使うので使わない
                    # auto_decoding_config=speech_v2.types.AutoDetectDecodingConfig(),
                    explicit_decoding_config=speech_v2.types.ExplicitDecodingConfig(
                        encoding=speech_v2.types.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
                        sample_rate_hertz=16000,
                        audio_channel_count=1
                    ),
                    language_codes=["ja-JP"],
                    model="latest_long",
                ),
            )

    async def process_queue(self):
        """音声キューを処理する"""
        current_stream_id = self._stream_id
        project = get_env_value("GOOGLE_CLOUD_PROJECT")
        logger.info(f"Starting streaming recognition with project: {project}")

        try:
            config_request = speech_v2.types.StreamingRecognizeRequest(
                recognizer=f'projects/{project}/locations/global/recognizers/_',
                streaming_config=self.streaming_config
            )
            yield config_request

            while self._is_streaming and self._stream_id == current_stream_id:
                try:
                    data = await self.queue.get()
                    audio_content = data["audio"]

                    request = speech_v2.types.StreamingRecognizeRequest(audio=audio_content)
                    yield request

                    self.queue.task_done()
                except Exception as e:
                    logger.error(f"Error in process_queue while processing audio: {str(e)}", exc_info=True)
                    continue
        except Exception as e:
            logger.error(f"Fatal error in process_queue: {str(e)}", exc_info=True)
            raise

    async def start_stream(self):
        """音声認識を実行し結果を処理する"""
        current_stream_id = self._stream_id
        logger.info(f"Starting new transcription stream (ID: {current_stream_id})")
        try:
            await self.initialize_client()
            stream = await self.client.streaming_recognize(
                requests=self.process_queue()
            )

            async for response in stream:
                # ストリームIDが変更された場合は処理を終了
                if self._stream_id != current_stream_id:
                    logger.info(f"Stream {current_stream_id} was terminated due to new stream request")
                    break

                if not response.results:
                    continue

                for result in response.results:
                    if not result.alternatives:
                        continue

                    transcription = result.alternatives[0].transcript
                    is_final = result.is_final

                    logger.info(f"Received transcript: {transcription} - FINAL: {is_final}")

                    await sio.emit(
                        "receive_audio_text",
                        {"text": transcription, "isFinal": is_final},
                        room=self.sid,
                    )

                    if is_final:
                        logger.info(f"Final transcription received for stream {current_stream_id}")
                        await self.restart_stream()
                        return

        except Exception as e:
            logger.error(f"Error in start_stream: {str(e)}", exc_info=True)
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
        asyncio.create_task(self.start_stream())

    async def stop_stream(self):
        """ストリーミングを停止する"""
        print(f"Stopping stream for {self.sid}")
        self._is_streaming = False
        self._cleanup_event.clear()  # イベントをリセット
        await self.cleanup_stream()
        await self._cleanup_event.wait()  # クリーンアップの完了を待機

    async def handle_responses(self, responses):
        """音声認識の結果を処理する"""
        try:
            async for response in responses:
                if not response.results:
                    continue

                for result in response.results:
                    if result.alternatives:
                        transcript = result.alternatives[0].transcript
                        is_final = result.is_final

                        await sio.emit(
                            "transcript",
                            {
                                "transcript": transcript,
                                "is_final": is_final
                            },
                            room=self.sid
                        )
        except Exception as e:
            logger.error(f"Error in handle_responses: {str(e)}", exc_info=True)