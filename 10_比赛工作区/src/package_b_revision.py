"""Stage, seal and verify the local engineering review deliverables.

AI assistance: ChatGPT (Codex, GPT-6.2 Sol), OpenAI, used 2026-11-21.
Public model release date was not verified. Assistance: packaging and QA.
"""
from argparse import ArgumentParser
from datetime import datetime, timedelta, timezone
from importlib.metadata import version
from pathlib import Path, PurePosixPath
from shutil import copyfile
from zipfile import ZIP_DEFLATED, ZipFile
import hashlib
import json
import re

from pypdf import PdfReader

from b_revision_data import DEFAULT_OUTPUT, file_hash, read_json, write_json
from problem_b_geometry import ROOT


STEM = "BSWBMCM2613050"
LIMIT = 20_000_000
BEIJING = timezone(timedelta(hours=8))
LOCK = datetime(2026,11,24,9,tzinfo=BEIJING)
DEADLINE = datetime(2026,11,24,10,tzinfo=BEIJING)
SOURCE_NAMES = ("problem_b_geometry.py","solve_problem_b.py","check_problem_b.py",
                "check_b_p4_cross.py","plot_problem_b.py","reproduce_b_revision.py")
REFERENCE_NAMES = ("B_P1.csv","B_P2_localization.csv","B_P2_fairness.csv","B_P3.csv","B_P4.csv")


def keep_each(files, out):
    with ZipFile(out,mode="x",compression=ZIP_DEFLATED,compresslevel=7) as archive:
        for rel, src in sorted(files.items()):
            archive.write(src,rel)
    assert out.stat().st_size < LIMIT
    return validate_archive(out)


def validate_archive(path):
    with ZipFile(path) as archive:
        names=archive.namelist()
        assert len(names)==len(set(names))
        for name in names:
            item=PurePosixPath(name)
            assert not (item.is_absolute() or ".." in item.parts or "\\" in name
                        or (item.parts and ":" in item.parts[0]))
        assert archive.testzip() is None
        return {key:hashlib.sha256(archive.read(key)).hexdigest() for key in names}


def stage(review, out):
    payload = {
        **{p.relative_to(ROOT).as_posix():p for p in (ROOT/"data").glob("B题题面*") if p.is_file()},
        **{f"results/{n}":ROOT/"results"/n for n in REFERENCE_NAMES},
        **{f"src/{n}":ROOT/"src"/n for n in SOURCE_NAMES},
        **{f"src/{p.name}":p for pattern in ("b_revision_*.py","b_replay*") for p in (ROOT/"src").glob(pattern)},
    }
    for name in ("results","figures","simulator"):
        for p in (review/name).rglob("*"):
            if p.is_file():
                payload["artifacts/"+p.relative_to(review).as_posix()]=p
    for name in ("B_submission.tex","B_submission.pdf","B_review_metrics.tex","P1_ERRATA.tex",
                 "P1_ERRATA.pdf","NUMBER_PROVENANCE.csv"):
        payload[f"artifacts/paper/{name}"]=review/"paper"/name
    for name in ("TEAM_HANDOFF_CHECKLIST.md","REPRODUCE.md","AI_USAGE_LOG.csv","requirements-review.txt"):
        payload[name]=review/name
    payload["artifacts/qa/PDF_CHECKS.json"]=review/"qa"/"PDF_CHECKS.json"
    result=keep_each(payload,out)
    assert "artifacts/paper/B_submission.tex" in result and "src/reproduce_b_revision.py" in result
    assert not any("cns" in f.lower() for f in result)
    print(f"Prepared {out.name}; {len(result)} members; {out.stat().st_size:,} bytes")
    return result


def seal(review, original_zip, reproduced):
    reproduced_qa=read_json(reproduced/"REPRODUCTION_CHECK.json")
    assert reproduced_qa["byte_matches"]>0 and len(reproduced_qa["pdf_text_matches"])==2
    base=validate_archive(original_zip)
    proof=review/"qa"/"REPRODUCTION_CHECK.json"
    copyfile(reproduced/"REPRODUCTION_CHECK.json",proof)
    support=review/(STEM+"fj.zip")
    additions=("VERIFY_REPORT.md","IMPROVEMENT_BACKLOG.md","qa/REPRODUCTION_CHECK.json")
    with (ZipFile(original_zip) as old, ZipFile(support,mode="x",compression=ZIP_DEFLATED,compresslevel=7) as new):
        for name in old.namelist():
            new.writestr(name,old.read(name))
        for name in additions:
            new.write(review/name,name)
    final=validate_archive(support)
    assert all(final[n]==sha for n,sha in base.items())
    signed=ROOT/"submission"/(STEM+"cns.pdf")
    submitted_paper=review/"paper"/"B_submission.pdf"
    reviewer=PdfReader(submitted_paper)
    assert not reviewer.metadata.author and not reviewer.attachments
    fulltext="".join(re.sub(r"\s+","",p.extract_text() or "") for p in reviewer.pages)
    assert "Teamreviewcopy" in fulltext and "Teamtextpending" in fulltext
    assert len(reviewer.pages)<=25
    assert all(path.stat().st_size<LIMIT for path in (signed,support,submitted_paper))
    moment=datetime.now(BEIJING)
    checks={
        "status":"team_review_edition",
        "submission_authorized":False,
        "checked_at_beijing":moment.isoformat(),
        "content_lock_beijing":LOCK.isoformat(),
        "submission_deadline_beijing":DEADLINE.isoformat(),
        "content_lock_already_passed":moment>=LOCK,
        "paper":{"official_filename":STEM+".pdf","review_file":"paper/B_submission.pdf",
                 "bytes":submitted_paper.stat().st_size,"sha256":file_hash(submitted_paper),
                 "pages":len(reviewer.pages),"empty_author_metadata":True,"attachments":0},
        "support":{"filename":support.name,"bytes":support.stat().st_size,"sha256":file_hash(support),
                   "member_count":len(final),"crc_passed":True,"member_sha256":final},
        "signed_commitment":{"filename":signed.name,"bytes":signed.stat().st_size,
                             "contents_and_signatures_reviewed":False},
        "reproduced_byte_matches":reproduced_qa["byte_matches"],
        "pdf_text_matches":reproduced_qa["pdf_text_matches"],
    }
    write_json(review/"RELEASE_ACCEPTANCE.json",checks)
    bundle=review/"SWB_2026_B_Engineering_Review.zip"
    keep_each({"B_submission_review.pdf":submitted_paper,"P1_ERRATA.pdf":review/"paper"/"P1_ERRATA.pdf",
               **{key:review/key for key in ("REPRODUCE.md","TEAM_HANDOFF_CHECKLIST.md","VERIFY_REPORT.md",
                  "IMPROVEMENT_BACKLOG.md","AI_USAGE_LOG.csv","RELEASE_ACCEPTANCE.json",
                  support.name)}},bundle)
    print("Sealed",support.name,support.stat().st_size,"bytes;",len(final),"members")
    print("Team bundle",bundle.name,bundle.stat().st_size,"bytes")


def requirements(out):
    out.write_text("\n".join(f"{package}=={version(package)}" for package in ("reportlab","pypdf","Pillow"))+"\n",
                   encoding="utf-8")


if __name__=="__main__":
    parser=ArgumentParser(description=__doc__)
    parser.add_argument("--review",type=Path,default=DEFAULT_OUTPUT)
    sub=parser.add_subparsers(dest="action",required=True)
    a=sub.add_parser("stage")
    a.add_argument("zip",type=Path)
    b=sub.add_parser("seal")
    b.add_argument("zip",type=Path)
    b.add_argument("rerun",type=Path)
    args=parser.parse_args()
    if args.action=="stage":
        requirements(args.review/"requirements-review.txt")
        stage(args.review,args.zip)
    else:
        seal(args.review,args.zip,args.rerun)
