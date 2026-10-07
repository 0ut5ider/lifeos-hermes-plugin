bool unit_need_daemon_reload(Unit *u) {
        assert(u);
        assert(u->manager);

        if (u->manager->unit_file_state_outdated)
                return true;

        /* For unit files, we allow masking… */
        if (fragment_mtime_newer(u->fragment_path, u->fragment_mtime,
                                 u->load_state == UNIT_MASKED))
                return true;

        /* Source paths should not be masked… */
        if (fragment_mtime_newer(u->source_path, u->source_mtime, false))
                return true;

        if (u->load_state == UNIT_LOADED) {
                _cleanup_strv_free_ char **dropins = NULL;

                (void) unit_find_dropin_paths(u, /* use_unit_path_cache= */ false, &dropins);

                if (!strv_equal(u->dropin_paths, dropins))
                        return true;

                /* … any drop-ins that are masked are simply omitted from the list. */
                STRV_FOREACH(path, u->dropin_paths)
                        if (fragment_mtime_newer(*path, u->dropin_mtime, false))
                                return true;
        }

        return false;
}
