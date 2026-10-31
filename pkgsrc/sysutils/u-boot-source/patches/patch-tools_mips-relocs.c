$NetBSD$

--- a/tools/mips-relocs.c
+++ b/tools/mips-relocs.c
@@ -36,13 +36,13 @@
 	case 1:							\
 		break;						\
 	case 2:							\
-		_val = is_be ? be16toh(_val) : le16toh(_val);	\
+		_val = is_be ? be16_to_cpu(_val) : le16_to_cpu(_val);	\
 		break;						\
 	case 4:							\
-		_val = is_be ? be32toh(_val) : le32toh(_val);	\
+		_val = is_be ? be32_to_cpu(_val) : le32_to_cpu(_val);	\
 		break;						\
 	case 8:							\
-		_val = is_be ? be64toh(_val) : le64toh(_val);	\
+		_val = is_be ? be64_to_cpu(_val) : le64_to_cpu(_val);	\
 		break;						\
 	}							\
 								\
@@ -63,13 +63,13 @@
 		_val = val;					\
 		break;						\
 	case 2:							\
-		_val = is_be ? htobe16(val) : htole16(val);	\
+		_val = is_be ? cpu_to_be16(val) : cpu_to_le16(val);	\
 		break;						\
 	case 4:							\
-		_val = is_be ? htobe32(val) : htole32(val);	\
+		_val = is_be ? cpu_to_be32(val) : cpu_to_le32(val);	\
 		break;						\
 	case 8:							\
-		_val = is_be ? htobe64(val) : htole64(val);	\
+		_val = is_be ? cpu_to_be64(val) : cpu_to_le64(val);	\
 		break;						\
 	default:						\
 		/* We should never reach here */		\
@@ -152,10 +152,10 @@
 	const Elf32_Rel *rel = _rel;
 	uint32_t off, type;
 
-	off = is_be ? be32toh(rel->r_offset) : le32toh(rel->r_offset);
+	off = is_be ? be32_to_cpu(rel->r_offset) : le32_to_cpu(rel->r_offset);
 	off -= text_base;
 
-	type = is_be ? be32toh(rel->r_info) : le32toh(rel->r_info);
+	type = is_be ? be32_to_cpu(rel->r_info) : le32_to_cpu(rel->r_info);
 	type = ELF32_R_TYPE(type);
 
 	return add_reloc(type, off);
@@ -166,7 +166,7 @@
 	const Elf64_Rela *rel = _rel;
 	uint64_t off, type;
 
-	off = is_be ? be64toh(rel->r_offset) : le64toh(rel->r_offset);
+	off = is_be ? be64_to_cpu(rel->r_offset) : le64_to_cpu(rel->r_offset);
 	off -= text_base;
 
 	type = rel->r_info >> (64 - 8);
@@ -207,7 +207,7 @@
 	Elf64_Shdr *shdr64;
 	struct stat st;
 	int err, fd;
-	void *elf;
+	uint8_t *elf;
 	bool skip;
 
 	fd = open(argv[1], O_RDWR);
@@ -230,8 +230,8 @@
 		goto out_close_fd;
 	}
 
-	ehdr32 = elf;
-	ehdr64 = elf;
+	ehdr32 = (const Elf32_Ehdr *)elf;
+	ehdr64 = (const Elf64_Ehdr *)elf;
 
 	if (memcmp(&ehdr32->e_ident[EI_MAG0], ELFMAG, SELFMAG)) {
 		fprintf(stderr, "Input file is not an ELF\n");
@@ -284,9 +284,10 @@
 		goto out_free_relocs;
 	}
 
-	shdr32 = elf + ehdr_field(e_shoff);
-	shdr64 = elf + ehdr_field(e_shoff);
-	shstrtab = elf + shdr_field(ehdr_field(e_shstrndx), sh_offset);
+	shdr32 = (Elf32_Shdr *)(elf + ehdr_field(e_shoff));
+	shdr64 = (Elf64_Shdr *)(elf + ehdr_field(e_shoff));
+	shstrtab = (const char *)(elf +
+			shdr_field(ehdr_field(e_shstrndx), sh_offset));
 
 	i_rel_shdr = UINT_MAX;
 	for (i = 0; i < ehdr_field(e_shnum); i++) {
