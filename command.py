# -*- coding: utf-8 -*-
import asyncio
import traceback

import jsons
import requests
from discord import ChannelType
from datetime import datetime

import consts
import utils


class Command:
    """
    Botのコマンドクラス.
    """
    __has_args: bool
    __cmd: str

    @property
    def config(self):
        return self.__config

    @property
    def cmd(self):
        return self.__cmd

    @property
    def has_args(self):
        return self.__has_args

    def __init__(self, config, cmd, has_args):
        """
        コンストラクタ.
        :param config: コンフィグ管理インスタンス.
        :type config: ASWDConfig
        :param cmd: コマンド.
        :type cmd: str
        :param has_args: コマンドが変数を受け取るか.
        :type has_args: bool
        """
        self.__config = config
        self.__cmd = cmd
        self.__has_args = has_args

    def usage(self):
        """
        使い方を返却する.
        各コマンドで説明を実装してください.
        :return: コマンドの使い方
        :rtype: str
        """
        raise NotImplementedError('コマンドサブクラスでexecute_cmdを実装してください.')

    def is_call(self, msg):
        """
        コマンドが呼び出されたか.
        :param msg: 書き込まれたメッセージ
        :type msg: str
        :return: 処理結果
        :rtype: bool
        """
        return msg.startswith(self.cmd)

    def is_cmd_help(self, msg):
        """
        コマンドのヘルプが呼び出されたか.
        :param msg: 書き込まれたメッセージ
        :type msg: str
        :return: 判定結果
        :rtype: bool
        """
        return self.cmd + " /?" == msg

    def is_valid(self, message):
        """
        バリデーションを行う.
        引数なしの場合、メッセージとコマンドが一致するか.
        引数ありの場合、メッセージがコマンド+空白で始まり、かつ、メッセージ長がコマンド+空白以上か.
        :param message: Discordメッセージインスタンス
        :type message: Message
        :return: 判定結果
        :rtype: bool
        """
        if self.has_args:
            return message.content.startswith(self.cmd + " ") and len(self.cmd) + 1 < len(message.content)
        else:
            return message.content == self.cmd

    def valid_custom(self, message, args):
        """
        コマンド固有のバリデーションを行う.
        引数ありのコマンドの場合、このメソッドをオーバーライドしてバリデーションを実装してください.
        :param message: Discordメッセージインスタンス
        :type message: Message
        :param args: コマンド引数
        :type args: str
        :return: 検証失敗時のメッセージ.検証成功の場合はNone.
        :rtype: str
        """
        return None

    async def execute(self, message):
        """
        コマンドを実行する.
        :param message: Discordメッセージインスタンス
        :type message: Message
        """
        print(self.cmd + " call.")
        if not message and not message.content:
            print("【エラー】Discordからコマンドが受け取れません. 再度入力してください.")
            return False
        if self.is_cmd_help(message):
            await self.send_message(message.channel, self.usage())
            print(self.cmd + " show help.")
            return False
        if not self.is_valid(message):
            msg = "コマンドが正しくありません.\n" + self.usage()
            await self.send_message(message.channel, msg)
            print(self.cmd + " failed valid.")
            return False
        args = message.content[len(self.cmd) + 1:]
        valid_msg = self.valid_custom(message, args)
        if valid_msg:
            msg = valid_msg + "\n" + self.usage()
            await self.send_message(message.channel, msg)
            print(self.cmd + " failed valid_custom.")
            return False
        await self.execute_cmd(message, args)
        print(self.cmd + " called.")

    async def execute_cmd(self, message, args):
        """
        コマンド固有の処理を実行する.
        各コマンドはメインの処理をここに実装してください.
        :param message: Discordメッセージインスタンス
        :type message: Message
        :param args: コマンド引数
        :type args: str
        :return: 処理結果
        :rtype: bool
        """
        raise NotImplementedError('コマンドサブクラスでexecute_cmdを実装してください.')

    async def send_message(self, channel, msg):
        """
        メッセージを送信する.
        :param channel: メッセージ送信先Channelインスタンス
        :type channel: ChannelType
        :param msg: 送信するメッセージ
        :type msg: str
        :return: 処理結果
        :rtype: bool
        """
        await utils.send_message(self.config.client, channel, msg)


class AllCommand(Command):
    """
    全コマンドを扱うコマンドクラス
    """

    @property
    def cmd_list(self):
        return self.__cmd_list

    def __init__(self, config, cmd, has_args, cmd_list):
        super().__init__(config, cmd, has_args)
        self.__cmd_list = cmd_list


class CommandManager:
    """
    コマンド管理クラス.
    コマンド実行はこのクラスの execute() にメッセージを食わせる.
    """

    def __init__(self, config):
        """
        コンストラクタ.
        コマンドクラス追加時は __cmd_list にコマンドインスタンスを追加すること.
        :param config: コンフィグ管理インスタンス
        :type config: ASWDConfig
        """

        self.__config = config
        self.__cmd_list = [
            StartCommand(config),
            StopCommand(config),
            AddBlackListCommand(config),
            DelBlackListCommand(config),
            ListBlackListCommand(config),
            AddServerCommand(config),
            DelServerCommand(config),
            StatusCommand(config),
            SetWatchWorldCommand(config),
            SetWatchIntervalCommand(config),
            SetPlayerSbnCountCommand(config),
            FuckYeahCommand(config)
        ]
        self.__help_cmd = HelpCommand(config, self.__cmd_list)
        self.__cmd_list.append(self.__help_cmd)

    async def execute(self, message):
        """
        コマンド実行.
        :param message: Discordのメッセージインスタンス
        :type message: Message
        :return: 処理結果
        :rtype: bool
        """

        # コマンド呼び出し判定
        if not message.content.startswith("/"):
            return False

        # コマンド判定
        call_cmd = None
        for cmd in self.__cmd_list:
            if cmd.is_call(message.content):
                call_cmd = cmd
                break
        if not call_cmd:
            # コマンドが存在しない場合ヘルプ表示
            msg = "コマンドが正しくありません.\n" + self.__help_cmd.usage()
            await utils.send_message(self.__config.client, message.channel, msg)
            return False

        return await call_cmd.execute(message)


class HelpCommand(AllCommand):
    """
    ヘルプを表示する.
    """

    def __init__(self, config, cmd_list):
        ret = []
        for cmd in cmd_list:
            if type(cmd) == HelpCommand:
                continue
            ret.append(cmd)
        super().__init__(config, "/?", False, ret)

    def usage(self):
        msg = "/? : ヘルプを表示します. /start /? のように入力するとコマンドのヘルプを表示します."
        return msg

    async def execute(self, message, args):
        ret = []
        ret.append(self.usage())
        for cmd in self.cmd_list:
            ret.append(cmd.usage())
        msg = "\n".join(ret)
        await self.send_message(message.channel, msg)
        return True


class StartCommand(Command):
    """
    サーバ監視開始コマンド.
    """

    def __init__(self, config):
        super().__init__(config, "/start", False)

    def usage(self):
        msg = "/start : 監視を開始します."
        return msg

    def valid_custom(self, message, args):
        if self.config.is_watch_started:
            return "監視継続します."

    async def execute(self, message):
        msg = "監視開始."
        await self.send_message(message.channel, msg)

        self.config.is_watch_started = True
        while self.config.is_watch_started:
            try:
                try:
                    print('WebServiceに接続開始.')
                    atlas_grids_json = requests.get(self.config.url).text
                    print("WebService接続成功.")
                    if not atlas_grids_json:
                        msg = '【エラー】jsonが空. 再度実行.'
                        print(msg)
                        await self.send_message(message.channel, msg)
                        await asyncio.sleep(self.config.watch_interval)
                        continue
                except Exception as e:
                    with open(consts.LOG_FILE, 'a') as f:
                        traceback.print_exc(file=f)
                    msg = '【エラー】WebService接続失敗. サーバダウンかも. 再度実行.'
                    print(msg)
                    await self.send_message(message.channel, msg)
                    await asyncio.sleep(self.config.watch_interval)
                    continue

                print('データ取得成功.')
                grids_dict = jsons.loads(atlas_grids_json)

                # サーバ情報収集
                servers_info = {}
                for grid in grids_dict["grids"]:
                    server_name = grid["grid"]
                    player_count = len(grid["players"])
                    player_sbn_count = 0
                    last_server_info = None
                    if len(self.config.last_servers_info) != 0 and server_name in self.config.last_servers_info:
                        last_server_info = self.config.last_servers_info[server_name]
                    if last_server_info is not None:
                        last_player_count = last_server_info["player_count"]
                        if last_player_count is not None:
                            player_sbn_count = player_count - last_player_count
                    players = grid["players"]
                    blacklist_players = []
                    for bl_player in blacklist_players:
                        for player in players:
                            player_name = player["name"]
                            if player_name.upper().find(bl_player.upper()) == -1:
                                continue
                            blacklist_players.append(player)

                    servers_info[server_name] = {
                        "server_name": server_name,
                        'player_count': player_count,
                        "player_sbn_count": player_sbn_count,
                        "blacklist_players": blacklist_players
                    }

                # サーバ情報を元に通知
                timestr = datetime.now().strftime("%m/%d %H:%M")
                tgt_channels = utils.get_channels(self.config.client)
                print("get_channels end. tgt_channels.len=", len(tgt_channels) > 0)
                if len(tgt_channels) > 0:
                    for tgt_channel in tgt_channels:
                        if tgt_channel.name.upper() not in servers_info:
                            msg = "{}　{}　データ取得エラー.".format(timestr, tgt_channel.name.upper())
                            await self.send_message(tgt_channel, msg)
                            continue
                        server_info = servers_info[tgt_channel.name.upper()]
                        if server_info is None:
                            continue

                        server_name = server_info["server_name"]
                        player_count = server_info["player_count"]
                        player_sbn_count = server_info["player_sbn_count"]
                        blacklist_players = server_info["blacklist_players"]

                        # 定例メッセージ送信
                        msg = "{}　{}　人数:{}　BL対象者:{}".format(timestr, server_name, player_count, blacklist_players)
                        await self.send_message(tgt_channel, msg)

                        # 警告メッセージ(人数急増)
                        if self.config.player_sbn_count <= player_sbn_count:
                            msg = "@everyone サーバ人数急増. 閾値:{} 増加人数:{}".format(self.config.player_sbn_count, player_sbn_count)
                            await self.send_message(tgt_channel, msg)

                        # 警告メッセージ(ブラックリスト対象の侵入)
                        if len(blacklist_players) > 0:
                            if server_name not in self.config.blacklist_notice_server_names:
                                msg = "@everyone ブラックリスト対象侵入. 対象:{}".format(blacklist_players)
                                await self.send_message(tgt_channel, msg)
                                self.config.blacklist_notice_server_names.append(server_name)

                        # 通常メッセージ(ブラックリスト対象者0になった)
                        if len(blacklist_players) == 0 and server_name in self.config.blacklist_notice_server_names:
                            msg = "ブラックリスト対象はいなくなりました."
                            await self.send_message(tgt_channel, msg)
                            self.config.blacklist_notice_server_names.remove(server_name)

                # 今回取得したサーバ情報を保持
                self.config.last_servers_info = servers_info
            except Exception as e:
                with open(consts.LOG_FILE, 'a') as f:
                    traceback.print_exc(file=f)
                msg = '【エラー】処理続行. 複数回発生したら/stopして.'
                print(msg)
                await self.send_message(message.channel, msg)

            await asyncio.sleep(self.config.watch_interval)
        return True


class StopCommand(Command):
    """
    サーバ監視終了コマンド.
    """

    def __init__(self, config):
        super().__init__(config, "/stop", False)

    def usage(self):
        msg = "/stop : 監視を終了します."
        return msg

    async def execute_cmd(self, message, args):
        self.config.is_watch_started = False
        await self.send_message(message.channel, "監視終了.")
        return True


class AddBlackListCommand(Command):
    """
    ブラックリスト追加コマンド.
    """

    def __init__(self, config):
        super().__init__(config, "/add bl", True)

    def usage(self):
        msg = "/add bl [プレイヤー名] : ブラックリストにプレイヤーを追加します."
        return msg

    def valid_custom(self, message, args):
        if not args:
            return "プレイヤー名を正しく入力してください."

    async def execute_cmd(self, message, args):
        self.config.add_blacklist(args)
        msg = "ブラックリストに追加しました."
        await self.send_message(message.channel, msg)
        return True


class DelBlackListCommand(Command):
    """
    ブラックリスト削除コマンド.
    """

    def __init__(self, config):
        super().__init__(config, "/dl bl", True)

    def usage(self):
        msg = "/del bl [プレイヤー名] : ブラックリストからプレイヤーを削除します."
        return msg

    def valid_custom(self, message, args):
        if not args:
            return "プレイヤー名を正しく入力してください."

    async def execute_cmd(self, message, args):
        self.config.del_blacklist(args)
        msg = "ブラックリストから削除しました."
        await self.send_message(message.channel, msg)
        return True


class ListBlackListCommand(Command):
    """
    ブラックリスト一覧表示コマンド.
    """

    def __init__(self, config):
        super().__init__(config, "/list bl", False)

    def usage(self):
        msg = "/list bl : ブラックリストの一覧を表示します."
        return msg

    async def execute_cmd(self, message, args):
        msg = "ブラックリスト: {}".format(self.config.blacklist)
        await self.send_message(message.channel, msg)
        return True


class AddServerCommand(Command):
    """
    監視対象サーバ追加コマンド.
    """

    def __init__(self, config):
        super().__init__(config, "/add server", True)

    def usage(self):
        msg = "/add server [サーバー名(A1-O15)] : Discordにサーバー監視報告用のチャンネルを追加します."
        return msg

    def valid_custom(self, message, args):
        if not args or args.upper() not in consts.SERVER_NAMES:
            return "サーバー名にA1～O15を設定してください."
        if utils.exists_channel(message.server, args):
            return "対象サーバは既に監視対象です."

    async def execute_cmd(self, message, args):
        print("サーバ監視報告チャンネル作成. name={}".format(args.upper()))
        await self.config.client.create_channel(message.server, args.upper(), type=ChannelType.text)
        print("サーバ監視報告チャンネル作成完了.")
        msg = "{}チャンネル追加. 監視情報はそこに出力します.".format(args.upper())
        await self.send_message(message.channel, msg)
        return True


class DelServerCommand(Command):
    """
    監視対象サーバ削除コマンド.
    """

    def __init__(self, config):
        super().__init__(config, "/del server", True)

    def usage(self):
        msg = "/del server [サーバー名(A1-O15)] : Discordのサーバー監視報告用のチャンネルを削除します."
        return msg

    def valid_custom(self, message, args):
        if not args or len(args) != 2 or args.upper() not in consts.SERVER_NAMES:
            return "サーバー名にA1～O15を設定してください."
        if not utils.exists_channel(message.server, args):
            return "対象サーバは監視対象ではありません."

    async def execute_cmd(self, message, args):
        print("サーバ監視報告チャンネル削除. name={}".format(args.upper()))
        channel = utils.exists_channel(message.server, args)
        await self.config.client.delete_channel(channel)
        print("サーバ監視報告チャンネル作成完了.")
        msg = "{}チャンネル削除.".format(args.upper())
        await self.send_message(message.channel, msg)
        return True


class StatusCommand(Command):
    """
    ステータス表示コマンド.
    """

    def __init__(self, config):
        super().__init__(config, "/status", False)

    def usage(self):
        msg = "/status : 設定値など現在の状態を表示します."
        return msg

    async def execute_cmd(self, message, args):
        msg_started = "監視中" if self.config.is_watch_started else "監視していません"
        msg = "監視状態:{}\n監視ワールド:{}\n監視間隔(秒):{}\n通知対象プレイヤー増加数:{}\nブラックリスト:{}\nブラックリスト侵入中サーバ:{}".format(
            msg_started, self.config.watch_world, self.config.watch_interval, self.config.player_sbn_count, self.config.blacklist, self.config.blacklist_notice_server_names)
        await self.send_message(message.channel, msg)
        return True


class SetWatchWorldCommand(Command):
    """
    監視ワールド設定コマンド.
    """

    def __init__(self, config):
        super().__init__(config, "/set world", True)

    def usage(self):
        msg = "/set world [NA or EU] : 監視ワールドを設定します."
        return msg

    def valid_custom(self, message, args):
        if not args:
            return "NA か EU を設定してください."
        if args != "NA" and args != "EU":
            return "NA か EU を設定してください."

    async def execute_cmd(self, message, args):
        self.config.watch_interval = args
        msg = "監視ワールドを{}秒に設定しました.".format(args)
        await self.send_message(message.channel, msg)
        return True


class SetWatchIntervalCommand(Command):
    """
    監視間隔設定コマンド.
    """

    def __init__(self, config):
        super().__init__(config, "/set interval", True)

    def usage(self):
        msg = "/set interval : 監視間隔(秒)を設定します."
        return msg

    def valid_custom(self, message, args):
        if not args or not args.isdecimal():
            return "監視間隔に数値を設定してください."


    async def execute_cmd(self, message, args):
        int_val = int(args)
        if int_val < 30:
            msg = "指定した数値が30秒未満のため、30秒を設定します."
            await self.send_message(message.channel, msg)
            int_val = 30
        self.config.watch_interval = int_val

        msg = "監視間隔を{}秒に設定しました.".format(int_val)
        await self.send_message(message.channel, msg)
        return True


class SetPlayerSbnCountCommand(Command):
    """
    通知対象プレイヤー増加数設定コマンド.
    """

    def __init__(self, config):
        super().__init__(config, "/set player_count", True)

    def usage(self):
        msg = "/set player_count : 通知対象プレイヤー増加数を設定します."
        return msg

    def valid_custom(self, message, args):
        if not args:
            return "プレイヤー増加数を数値で設定してください."

    async def execute_cmd(self, message, args):
        int_val = int(args)
        if int_val < 3:
            msg = "指定した数値が3人未満のため、3人を設定します."
            await self.send_message(message.channel, msg)
            int_val = 3
        self.config.player_sbn_count = int_val

        msg = "通知対象プレイヤー増加数を{}人に設定しました.".format(int_val)
        await self.send_message(message.channel, msg)
        return True


class FuckYeahCommand(Command):
    """
    Fuck YEAH !!
    """

    def __init__(self, config):
        super().__init__(config, "/fuck", True)

    def usage(self):
        msg = "/fuck xxx : Fuck YEAH !!"
        return msg

    async def execute_cmd(self, message, args):
        msg = "Fuck YEAH !!"
        await self.send_message(message.channel, msg)
        msg = "https://www.youtube.com/watch?v=IhnUgAaea4M&feature=youtu.be&t=8"
        await self.send_message(message.channel, msg)
        return True
