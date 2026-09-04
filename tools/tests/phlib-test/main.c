/*
 * Copyright (c) 2022 Winsider Seminars & Solutions, Inc.  All rights reserved.
 *
 * This file is part of System Informer.
 *
 * Authors:
 *
 *     wj32    2010-2016
 *
 */

#include "tests.h"

int __cdecl wmain(int argc, wchar_t *argv[])
{
    NTSTATUS status;

    status = PhInitializePhLib(L"phlib-test");
    if (!NT_SUCCESS(status))
        return 1;

    Test_basesup();
    Test_avltree();
    Test_format();
    Test_util();
    Test_resource();

    return 0;
}
