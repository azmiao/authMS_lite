from datetime import datetime

import hoshino
import nonebot
import pytz
from nonebot import on_notice, on_command, NoticeSession

from . import util
from .constant import group_dict, trial_list, config

tz = pytz.timezone('Asia/Shanghai')


@on_notice('group_decrease.kick_me')
async def kick_me_alert(session: NoticeSession):
    """
    被踢出同样记录
    """
    group_id = session.event.group_id
    operator_id = session.event.operator_id
    util.log(f'被{operator_id}踢出群{group_id}', 'group_kick')


@on_command('退群', only_to_me=False)
async def group_leave_chat(session):
    """
    退群, 并不影响授权, 清除授权请试用清除授权命令
    """
    if session.event.user_id not in hoshino.config.SUPERUSERS:
        await session.finish('只有主人才能让我退群哦')
        return
    gid = int(session.current_arg.strip())
    await session.send('正在褪裙...')

    rt_code = await util.gun_group(group_id=gid, reason='管理员操作')
    if rt_code:
        await session.send(f'已成功退出群{gid}')
        util.log(f'已成功退出群{gid}', 'group_leave')
    else:
        await session.send(f'退出群{gid}时发生错误')
        util.log(f'退出群{gid}时发生错误', 'group_leave')


@on_command('快速检查', only_to_me=True)
async def quick_check_chat(session):
    """
    立即执行一次检查, 内容与定时任务一样
    """
    if session.event.user_id not in hoshino.config.SUPERUSERS:
        return
    await check_auth()
    await session.finish('检查完成')


async def check_auth():
    """
    检查所有已加入群的授权状态, 和人数
    """
    bot = nonebot.get_bot()

    # 该函数会独立地检查一次所有群的人数是否超标
    await check_number()

    group_info_all = await util.get_group_list_all()
    for group in group_info_all:
        gid = group['group_id']
        if gid in group_dict:
            util.log(f'正在检查群{gid}的授权......')
            # 此群已有授权或曾有授权, 检查是否过期
            time_left = group_dict[gid] - datetime.now()
            days_left = time_left.days

            rt_code = util.allow_list(gid)
            if rt_code == 'no_check' or rt_code == 'no_auth_check':
                # 在白名单, 并不会影响过期事件
                continue
        
            if time_left.total_seconds() <= 0:
                # 已过期, 检查是否在白名单中

                if config.AUTO_LEAVE and time_left.total_seconds() < -config.LEAVE_AFTER_DAYS * 86400:
                    # 自动退群且已过期超过LEAVE_AFTER_DAYS天, 如果设置LEAVE_AFTER_DAYS为0则立刻退群
                    await util.gun_group(group_id=gid, reason='授权过期')
                    util.log(f'群{gid}授权过期,已自动退群', 'group_leave')
                else:
                    # 不自动退群, 只发消息提醒
                    t_sp = '【提醒】本群授权已过期\n'
                    e_sp = '如果需要续费请联系机器人维护'
                    gname_sp = group['group_name']
                    msg_expired = await util.process_group_msg(gid=gid, expiration=group_dict[gid], title=t_sp,
                                                               end=e_sp, group_name_sp=gname_sp)
                    try:
                        await bot.send_group_msg(group_id=gid, message=msg_expired)
                    except Exception as e:
                        util.log(f'向群{gid}发送过期提醒时发生错误{type(e)}')
                group_dict.pop(gid)
                await util.flush_group()
            if config.REMIND_BEFORE_EXPIRED > days_left >= 0:
                # 将要过期
                msg_remind = await util.process_group_msg(
                    gid=gid,
                    expiration=group_dict[gid],
                    title=f'【提醒】本群的授权已不足{days_left + 1}天\n',
                    end='\n如果需要续费请联系机器人维护',
                    group_name_sp=group['group_name'])
                try:
                    await bot.send_group_msg(group_id=gid,
                                             message=msg_remind)
                except Exception as e:
                    hoshino.logger.error(f'向群{gid}发生到期提醒消息时发生错误{type(e)}')
            util.log(f'群{gid}的授权不足{days_left + 1}天')

        elif gid not in trial_list:
            # 正常情况下, 无论是50人以上群还是50人以下群, 都需要经过机器人同意或检查
            # 但是！如果机器人掉线期间被拉进群试用, 将无法处理试用, 因此有了这部分憨批代码

            if not config.NEW_GROUP_DAYS and config.AUTO_LEAVE:
                # 无新群试用机制,直接退群
                await util.gun_group(group_id=gid, reason='无授权')
                util.log(f'发现无记录而被拉入的新群{gid}, 已退出此群', 'group_leave')
            else:
                await util.new_group_check(gid)
                util.log(f'发现无记录而被拉入的新群{gid}, 已开始试用', 'group_add')


async def check_number(group_id=0):
    """
    检查所有群的成员数量是否符合要求, 当传入group_id时则检查传入的群
    """
    if group_id == 0:
        gnums = await util.get_group_info(info_type='member_count')
    else:
        __gid = group_id
        gnums = await util.get_group_info(group_ids=__gid, info_type='member_count')
    for gid in gnums:
        if gnums[gid] > config.MAX_GROUP_NUM:
            # 人数超过, 检测是否在白名单 
            rt_code = util.allow_list(gid)
            if rt_code == 'not in' or rt_code == 'no_check_auth':
                util.log(f'群{gid}人数超过设定值, 当前人数{gnums[gid]}, 白名单状态{rt_code}', 'number_check')
                if group_id == 0:
                    # 检查全部群的情况, 可以自动退出
                    if config.AUTO_LEAVE:
                        await util.gun_group(group_id=gid, reason='群人数超过管理员设定的最大值')
                    else:
                        await util.notify_group(group_id=gid, txt='群人数超过管理员设定的最大值, 请联系管理员')
                else:
                    # 检查单个群的情况, 只通知而不自动退出, 等到下次计划任务时再退出
                    await util.notify_group(group_id=gid, txt='群人数超过管理员设定的最大值, 请联系管理员')
                    return 'overflow'
    return None
