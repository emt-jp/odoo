# -*- coding: utf-8 -*-

from . import models


def post_init_hook(env):
    """Assign restaurant roles to all users after module installation."""
    import logging
    _logger = logging.getLogger(__name__)

    try:
        users = env['res.users'].search([('active', '=', True)])

        manager_group = env.ref('restaurant_management.group_restaurant_manager')
        waiter_group = env.ref('restaurant_management.group_restaurant_waiter')

        admin_count = 0
        waiter_count = 0

        for user in users:
            if user.has_group('base.group_system'):
                # Add manager group using SQL directly to avoid write restrictions
                env.cr.execute("""
                    INSERT INTO res_groups_users_rel (gid, uid)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                """, (manager_group.id, user.id))
                admin_count += 1
            else:
                # Add waiter group
                env.cr.execute("""
                    INSERT INTO res_groups_users_rel (gid, uid)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                """, (waiter_group.id, user.id))
                waiter_count += 1

        _logger.info(f"Restaurant roles assigned: {admin_count} managers, {waiter_count} waiters")
    except Exception as e:
        _logger.error(f"Error assigning restaurant roles: {e}")
