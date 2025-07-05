def parse_git_diff_to_old_version(diff_text):
    """
    Parse git diff output and extract old version of each changed section.
    
    Args:
        diff_text (str): Output from 'git diff -W' command
    
    Returns:
        list: List of dictionaries containing file info, diff part, and old version content
    """
    lines = diff_text.strip().split('\n')
    result = []
    current_file = None
    current_hunk = []
    current_diff_part = []
    in_hunk = False
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check for file header (diff --git)
        if line.startswith('diff --git'):
            # Save previous hunk if exists
            if current_file and current_hunk:
                old_content = generate_old_version(current_hunk)
                result.append({
                    'file': current_file,
                    'diff_part': '\n'.join(current_diff_part),
                    'old_version': old_content
                })
            
            # Extract file paths
            parts = line.split()
            if len(parts) >= 4:
                current_file = parts[3][2:]  # Remove 'b/' prefix
            current_hunk = []
            current_diff_part = [line]  # Start new diff part with file header
            in_hunk = False
            
        # Check for hunk header (@@)
        elif line.startswith('@@'):
            # Save previous hunk if exists
            if current_file and current_hunk:
                old_content = generate_old_version(current_hunk)
                result.append({
                    'file': current_file,
                    'diff_part': '\n'.join(current_diff_part),
                    'old_version': old_content
                })
            
            current_hunk = []
            current_diff_part = []
            in_hunk = True
            
            # Add the @@ line to diff part
            current_diff_part.append(line)
            
            # Check if there's code after the @@ header
            # Format: @@ -old_start,old_count +new_start,new_count @@ optional_function_context
            if '@@' in line[2:]:  # Look for second @@ 
                parts = line.split('@@')
                if len(parts) >= 3 and parts[2].strip():
                    # There's code after the @@, treat it as context
                    context_code = parts[2].strip()
                    current_hunk.append(' ' + context_code)  # Add as context line
            
        # Process hunk content
        elif in_hunk and (line.startswith('+') or line.startswith('-') or line.startswith(' ')):
            current_hunk.append(line)
            current_diff_part.append(line)
            
        # Handle other lines (index, mode changes, etc.)
        elif current_diff_part:  # Only add if we're in a diff context
            current_diff_part.append(line)
            if in_hunk and not line.startswith('index') and not line.startswith('---') and not line.startswith('+++'):
                current_hunk.append(line)
        
        i += 1
    
    # Handle last hunk
    if current_file and current_hunk:
        old_content = generate_old_version(current_hunk)
        result.append({
            'file': current_file,
            'diff_part': '\n'.join(current_diff_part),
            'old_version': old_content
        })
    
    return result


def generate_old_version(hunk_lines):
    """
    Generate old version content from a hunk by removing '+' lines 
    and '-' prefixes from remaining lines.
    
    Args:
        hunk_lines (list): Lines from a diff hunk
    
    Returns:
        str: Old version content
    """
    old_lines = []
    
    for line in hunk_lines:
        if line.startswith('+'):
            # Skip lines that were added (not in old version)
            continue
        elif line.startswith('-'):
            # Remove '-' prefix from deleted lines (they were in old version)
            old_lines.append(line[1:])
        elif line.startswith(' '):
            # Context lines (unchanged) - remove space prefix
            old_lines.append(line[1:])
        else:
            # Handle any other lines (shouldn't happen in normal diff)
            old_lines.append(line)
    
    return '\n'.join(old_lines)


# Example usage
if __name__ == "__main__":
    # Sample git diff output with code in @@ line
    sample_diff = """diff --git a/src/file_io.c b/src/file_io.c
index 26d3d6d..6ccab78 100644
--- a/src/file_io.c
+++ b/src/file_io.c
@@ -1,65 +1,65 @@
 /*
-** Copyright (C) 2002-2013 Erik de Castro Lopo <erikd@mega-nerd.com>
+** Copyright (C) 2002-2014 Erik de Castro Lopo <erikd@mega-nerd.com>
 ** Copyright (C) 2003 Ross Bencina <rbencina@iprimus.com.au>
 **
 ** This program is free software; you can redistribute it and/or modify
 ** it under the terms of the GNU Lesser General Public License as published by
 ** the Free Software Foundation; either version 2.1 of the License, or
 ** (at your option) any later version.
 **
 ** This program is distributed in the hope that it will be useful,
 ** but WITHOUT ANY WARRANTY; without even the implied warranty of
 ** MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 ** GNU Lesser General Public License for more details.
 **
 ** You should have received a copy of the GNU Lesser General Public License
 ** along with this program; if not, write to the Free Software
 ** Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
 */
 
 /*
 **	The file is split into three sections as follows:
 **		- The top section (USE_WINDOWS_API == 0) for Linux, Unix and MacOSX
 **			systems (including Cygwin).
 **		- The middle section (USE_WINDOWS_API == 1) for microsoft windows
 **			(including MinGW) using the native windows API.
 **		- A legacy windows section which attempted to work around grevious
 **			bugs in microsoft's POSIX implementation.
 */
 
 /*
 **	The header file sfconfig.h MUST be included before the others to ensure
 **	that large file support is enabled correctly on Unix systems.
 */
 
 #include "sfconfig.h"
 
 #include <stdio.h>
 #include <stdlib.h>
 
 #if HAVE_UNISTD_H
 #include <unistd.h>
 #endif
 
 #if (HAVE_DECL_S_IRGRP == 0)
 #include <sf_unistd.h>
 #endif
 
 #include <string.h>
 #include <fcntl.h>
 #include <errno.h>
 #include <sys/stat.h>
 
 #include "sndfile.h"
 #include "common.h"
 
 #define	SENSIBLE_SIZE	(0x40000000)
 
 /*
 **	Neat solution to the Win32/OS2 binary file flage requirement.
 **	If O_BINARY isn't already defined by the inclusion of the system
 **	headers, set it to zero.
 */
 #ifndef O_BINARY
 #define O_BINARY 0
 #endif
@@ -357,39 +357,42 @@ sf_count_t
 psf_fwrite (const void *ptr, sf_count_t bytes, sf_count_t items, SF_PRIVATE *psf)
 {	sf_count_t total = 0 ;
 	ssize_t	count ;
 
+	if (bytes == 0 || items == 0)
+		return 0 ;
+
 	if (psf->virtual_io)
 		return psf->vio.write (ptr, bytes*items, psf->vio_user_data) / bytes ;
 
 	items *= bytes ;
 
 	/* Do this check after the multiplication above. */
 	if (items <= 0)
 		return 0 ;
 
 	while (items > 0)
 	{	/* Break the writes down to a sensible size. */
 		count = (items > SENSIBLE_SIZE) ? SENSIBLE_SIZE : items ;
 
 		count = write (psf->file.filedes, ((const char*) ptr) + total, count) ;
 
 		if (count == -1)
 		{	if (errno == EINTR)
 				continue ;
 
 			psf_log_syserr (psf, errno) ;
 			break ;
 			} ;
 
 		if (count == 0)
 			break ;
 
 		total += count ;
 		items -= count ;
 		} ;
 
 	if (psf->is_pipe)
 		psf->pipeoffset += total ;
 
 	return total / bytes ;
 } /* psf_fwrite */
"""
    
    results = parse_git_diff_to_old_version(sample_diff)
    
    for i, item in enumerate(results):
        print(f"=== Change {i+1} ===")
        print(f"File: {item['file']}")
        print("\nDiff part:")
        print(item['diff_part'])
        print("\nOld version:")
        print(item['old_version'])
        print("=" * 50)