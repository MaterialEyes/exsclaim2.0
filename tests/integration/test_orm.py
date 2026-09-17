from datetime import datetime, timezone

from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

import exsclaim
import pytest


async def upload_test_data(db: AsyncSession):
	await db.execute(insert(exsclaim.User).values({
		"id": UUID("01a0b121-ad60-71bb-a9a8-3c5ea4a72588"),
		"name": "Test",
		"orcid": "0000-0000-0000-0000"
	}))

	run_id = UUID("019ba4c7-b23f-7e32-b072-a104b88183d4")
	await db.execute(insert(exsclaim.Run).values([
		{
			"id": run_id,
			"start_time": datetime(2026, 1, 9, 22, 1, 49, 370801, tzinfo=timezone.utc),
			"end_time": datetime(2026, 1, 9, 22, 8, 51, 579939, tzinfo=timezone.utc),
			"search_query": {"llm": "llama3.3", "name": "user_test_break", "open": False,
			                 "query": {"search_field_1": {"term": "battery spectra", "synonyms": []}},
			                 "run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4", "sortby": "relevant", "model_key": True,
			                 "save_format": ["subfigures", "visualization", "boxes", "postgres", "csv"],
			                 "journal_family": "nature", "maximum_scraped": 5},
			"extension": "tar.gz",
			"status": "Finished",
			"publicize_results": False
		}
	]))

	await db.execute(insert(exsclaim.Article).values([
		{
			"id": "s41467-025-66082-3",
			"title": "Fluorine-free binder-based dry thick electrodes with Parafilm® M toward sustainable and efficient battery manufacturing | Nature Communications",
			"url": "https://www.nature.com/articles/s41467-025-66082-3",
			"license": "http://creativecommons.org/licenses/by-nc-nd/4.0/",
			"open": True,
			"abstract": None
		}
	]))

	await db.execute(insert(exsclaim.Author).values([
		{
			"id": "01a0b0d8-73e0-7aca-ac5f-edcbde705c65",
			"name": "Seung Min Lee",
			"orcid": None
		},
		{
			"id": "01a0b0d8-73e0-7af0-a9ba-31a7311966bb",
			"name": "Hyunwoo Choi",
			"orcid": None
		},
		{
			"id": "01a0b0d8-73e0-7b1c-bbac-6ddae34ac7ad",
			"name": "Huiyeol Lee",
			"orcid": None
		},
		{
			"id": "01a0b0d8-73e0-7c07-9972-da377190a252",
			"name": "Jinsoo Kim",
			"orcid": None
		},
		{
			"id": "01a0b0d8-73e0-7c12-b7dd-db1fb18a0900",
			"name": "Hyeseong Oh",
			"orcid": None
		},
		{
			"id": "01a0b0d8-73e0-7cd3-bc34-f4d543222f7c",
			"name": "Wook Ryol Hwang",
			"orcid": None
		},
		{
			"id": "01a0b0d8-73e0-7e98-aab2-55ee4cdde5a0",
			"name": "Sinho Choi",
			"orcid": None
		},
		{
			"id": "01a0b0d8-73e0-7eff-bf5e-07009a8fea4d",
			"name": "Taegyun Yu",
			"orcid": "0009-0008-4004-0548"
		},
		{
			"id": "01a0b0d8-73e0-7f16-a3c9-f4ddf9ae4f27",
			"name": "Jieun Nam",
			"orcid": None
		},
		{
			"id": "01a0b0d8-73e0-7f21-ac7c-ee2146917588",
			"name": "Kwon-Hyung Lee",
			"orcid": None
		},
		{
			"id": "01a0b0d8-73e0-7fed-a86d-d5e5997a2e98",
			"name": "Kyeong-Min Jeong",
			"orcid": None
		},
		{
			"id": "01a0b0d8-73e1-7123-b2f4-ccb4aa4cb336",
			"name": "Jung-Keun Yoo",
			"orcid": None
		},
		{
			"id": "01a0b0d8-73e1-713a-a214-0ec1c6a9ec72",
			"name": "Juho Lee",
			"orcid": None
		},
		{
			"id": "01a0b0d8-73e1-7274-85a2-6a5ad63eac47",
			"name": "Wooyoung Jin",
			"orcid": None
		},
		{
			"id": "01a0b0d8-73e1-727f-b117-48bbd1eaba31",
			"name": "Hyeongseok Shim",
			"orcid": None
		},
		{
			"id": "01a0b0d8-73e1-7317-90c7-592c57fe0056",
			"name": "Dongoh Kim",
			"orcid": None
		},
		{
			"id": "01a0b0d8-73e1-7322-88cc-4adde23255ce",
			"name": "Joonhee Kang",
			"orcid": None
		},
		{
			"id": "01a0b0d8-73e1-732e-8135-1f167cf188a5",
			"name": "Jinwoo Seong",
			"orcid": None
		},
		{
			"id": "01a0b0d8-73e1-7339-9d07-087834d59240",
			"name": "Tae-Hee Kim",
			"orcid": None
		},
		{
			"id": "01a0b0d8-73e1-73e5-801e-8e69d42814cb",
			"name": "Sanghyun Song",
			"orcid": None
		},
		{
			"id": "01a0b0d8-73e1-7599-aa93-b2738f42ee00",
			"name": "Gyujin Song",
			"orcid": None
		},
		{
			"id": "01a0b0d8-73e1-767e-9982-37404734b464",
			"name": "Hyungyeon Cha",
			"orcid": None
		},
		{
			"id": "01a0b0d8-73e1-76c0-9a8b-a4d5470fe33f",
			"name": "Joong Tark Han",
			"orcid": None
		},
		{
			"id": "01a0b0d8-73e1-77c6-831c-19259476835d",
			"name": "Min Kyung Kim",
			"orcid": "0009-0005-1183-3520"
		},
		{
			"id": "01a0b0d8-73e1-7913-8efd-effdc3d79ba3",
			"name": "Myoungkeon Park",
			"orcid": None
		},
		{
			"id": "01a0b0d8-73e1-7a05-90c0-d7ae6ad79780",
			"name": "Minjong Seong",
			"orcid": None
		},
		{
			"id": "01a0b0d8-73e1-7a57-b556-0edb603ff4c2",
			"name": "Min Jin Lim",
			"orcid": None
		},
		{
			"id": "01a0b0d8-73e1-7a9b-a21d-1636c9e2c4b1",
			"name": "Sungbin Jang",
			"orcid": None
		},
		{
			"id": "01a0b0d8-73e1-7af6-a17d-999a8676c4d0",
			"name": "Hun-Gi Jung",
			"orcid": None
		},
		{
			"id": "01a0b0d8-73e1-7b6c-97d6-c74d2e8f145a",
			"name": "Sanghoon Jo",
			"orcid": None
		},
		{
			"id": "01a0b0d8-73e1-7b8e-ad47-a8681a7f1422",
			"name": "Min Jang",
			"orcid": None
		}
	]))

	await db.execute(insert(exsclaim.ArticleAuthor).values([
		{
			"article_id": "s41467-025-66082-3",
			"author_id": "01a0b0d8-73e0-7f21-ac7c-ee2146917588",
			"author_order": 1
		},
		{
			"article_id": "s41467-025-66082-3",
			"author_id": "01a0b0d8-73e1-7a9b-a21d-1636c9e2c4b1",
			"author_order": 2
		},
		{
			"article_id": "s41467-025-66082-3",
			"author_id": "01a0b0d8-73e1-713a-a214-0ec1c6a9ec72",
			"author_order": 3
		},
		{
			"article_id": "s41467-025-66082-3",
			"author_id": "01a0b0d8-73e1-7a57-b556-0edb603ff4c2",
			"author_order": 4
		},
		{
			"article_id": "s41467-025-66082-3",
			"author_id": "01a0b0d8-73e1-7317-90c7-592c57fe0056",
			"author_order": 5
		},
		{
			"article_id": "s41467-025-66082-3",
			"author_id": "01a0b0d8-73e1-7322-88cc-4adde23255ce",
			"author_order": 6
		},
		{
			"article_id": "s41467-025-66082-3",
			"author_id": "01a0b0d8-73e1-732e-8135-1f167cf188a5",
			"author_order": 7
		},
		{
			"article_id": "s41467-025-66082-3",
			"author_id": "01a0b0d8-73e1-7339-9d07-087834d59240",
			"author_order": 8
		},
		{
			"article_id": "s41467-025-66082-3",
			"author_id": "01a0b0d8-73e1-7123-b2f4-ccb4aa4cb336",
			"author_order": 9
		},
		{
			"article_id": "s41467-025-66082-3",
			"author_id": "01a0b0d8-73e1-7a05-90c0-d7ae6ad79780",
			"author_order": 10
		},
		{
			"article_id": "s41467-025-66082-3",
			"author_id": "01a0b0d8-73e0-7b1c-bbac-6ddae34ac7ad",
			"author_order": 11
		},
		{
			"article_id": "s41467-025-66082-3",
			"author_id": "01a0b0d8-73e0-7f16-a3c9-f4ddf9ae4f27",
			"author_order": 12
		},
		{
			"article_id": "s41467-025-66082-3",
			"author_id": "01a0b0d8-73e1-7b8e-ad47-a8681a7f1422",
			"author_order": 13
		},
		{
			"article_id": "s41467-025-66082-3",
			"author_id": "01a0b0d8-73e1-7274-85a2-6a5ad63eac47",
			"author_order": 14
		},
		{
			"article_id": "s41467-025-66082-3",
			"author_id": "01a0b0d8-73e1-727f-b117-48bbd1eaba31",
			"author_order": 15
		},
		{
			"article_id": "s41467-025-66082-3",
			"author_id": "01a0b0d8-73e1-7b6c-97d6-c74d2e8f145a",
			"author_order": 16
		},
		{
			"article_id": "s41467-025-66082-3",
			"author_id": "01a0b0d8-73e0-7aca-ac5f-edcbde705c65",
			"author_order": 17
		},
		{
			"article_id": "s41467-025-66082-3",
			"author_id": "01a0b0d8-73e0-7af0-a9ba-31a7311966bb",
			"author_order": 18
		},
		{
			"article_id": "s41467-025-66082-3",
			"author_id": "01a0b0d8-73e1-7af6-a17d-999a8676c4d0",
			"author_order": 19
		},
		{
			"article_id": "s41467-025-66082-3",
			"author_id": "01a0b0d8-73e0-7c07-9972-da377190a252",
			"author_order": 20
		},
		{
			"article_id": "s41467-025-66082-3",
			"author_id": "01a0b0d8-73e0-7fed-a86d-d5e5997a2e98",
			"author_order": 21
		},
		{
			"article_id": "s41467-025-66082-3",
			"author_id": "01a0b0d8-73e0-7c12-b7dd-db1fb18a0900",
			"author_order": 22
		},
		{
			"article_id": "s41467-025-66082-3",
			"author_id": "01a0b0d8-73e1-7913-8efd-effdc3d79ba3",
			"author_order": 23
		},
		{
			"article_id": "s41467-025-66082-3",
			"author_id": "01a0b0d8-73e0-7cd3-bc34-f4d543222f7c",
			"author_order": 24
		},
		{
			"article_id": "s41467-025-66082-3",
			"author_id": "01a0b0d8-73e1-73e5-801e-8e69d42814cb",
			"author_order": 25
		},
		{
			"article_id": "s41467-025-66082-3",
			"author_id": "01a0b0d8-73e1-77c6-831c-19259476835d",
			"author_order": 26
		},
		{
			"article_id": "s41467-025-66082-3",
			"author_id": "01a0b0d8-73e1-76c0-9a8b-a4d5470fe33f",
			"author_order": 27
		},
		{
			"article_id": "s41467-025-66082-3",
			"author_id": "01a0b0d8-73e1-767e-9982-37404734b464",
			"author_order": 28
		},
		{
			"article_id": "s41467-025-66082-3",
			"author_id": "01a0b0d8-73e1-7599-aa93-b2738f42ee00",
			"author_order": 29
		},
		{
			"article_id": "s41467-025-66082-3",
			"author_id": "01a0b0d8-73e0-7e98-aab2-55ee4cdde5a0",
			"author_order": 30
		},
		{
			"article_id": "s41467-025-66082-3",
			"author_id": "01a0b0d8-73e0-7eff-bf5e-07009a8fea4d",
			"author_order": 31
		}
	]))

	await db.execute(insert(exsclaim.RunArticles).values({
		"run_id": run_id,
		"article_id": "s41467-025-66082-3",
		"article_order": 1,
	}))

	await db.execute(insert(exsclaim.Figure).values([
		{
			"id": "s41467-025-66082-3-fig2",
			"caption": "a FTIR spectra demonstrating C-F and C-H bond signals. b DSC curves featuring Tg of binders. c HOMO-LUMO energy gap of polymer segments estimate an electrochemical window.",
			"url": "https://media.springernature.com/full/springer-static/image/art%3A10.1038%2Fs41467-025-66082-3/MediaObjects/41467_2025_66082_Fig2_HTML.png",
			"figure_path": "user_test_break/figures/s41467-025-66082-3_fig2.png",
			"article_id": "s41467-025-66082-3",
		},
		{
			"id": "s41467-025-66082-3-fig1",
			"caption": "Comparison of PTFE, PVDF, and Parafilm binders based on structure, cost, environmental impact, and manufacturing process. a–c The binder chemistry comparison represents the molecular structure. The comparisons of d materials cost and e GWP to identify the economic and environmental impact. f The potential fabrication process schematics on the powder-to-electrode concept involved pressing and pattern-coated electrode formation.",
			"url": "https://media.springernature.com/full/springer-static/image/art%3A10.1038%2Fs41467-025-66082-3/MediaObjects/41467_2025_66082_Fig1_HTML.png",
			"figure_path": "user_test_break/figures/s41467-025-66082-3_fig1.png",
			"article_id": "s41467-025-66082-3",
		},
		{
			"id": "s41467-025-66082-3-fig3",
			"caption": "a Depth-dependent cohesion measurement of electrodes b Adhesion measurement with and without primer coating. The error bars represent the standard deviation (σ) from three independent measurements for each experimental group. The adhesion and cohesion values were determined as the averaged horizontal force measured within the defined loading region. The cross-sectional SEM and C atom EDS mapping images of c, f PTFE, d, g PVDF, and e, h Parafilm-based ones were used to determine the CBD distribution and microstructural defects. i–l 3D reconstructed image from FIB-SEM analysis for the microstructure and material distribution of Parafilm-based dry electrodes.",
			"url": "https://media.springernature.com/full/springer-static/image/art%3A10.1038%2Fs41467-025-66082-3/MediaObjects/41467_2025_66082_Fig3_HTML.png",
			"figure_path": "user_test_break/figures/s41467-025-66082-3_fig3.png",
			"article_id": "s41467-025-66082-3",
		},
		{
			"id": "s41467-025-66082-3-fig4",
			"caption": "Nyquist EIS data for a PTFE, b PVDF, and c Parafilm-based electrodes. d The ionic tortuosities and e–h DCIR comparison for those binder-based electrodes to identify the comprehensive resistance. (1 C = 200 mA g−1).",
			"url": "https://media.springernature.com/full/springer-static/image/art%3A10.1038%2Fs41467-025-66082-3/MediaObjects/41467_2025_66082_Fig4_HTML.png",
			"figure_path": "user_test_break/figures/s41467-025-66082-3_fig4.png",
			"article_id": "s41467-025-66082-3",
		},
		{
			"id": "s41467-025-66082-3-fig5",
			"caption": "Rate capabilities in half-cell configuration for a PTFE, b PVDF, and c Parafilm. The cycling profile of full cells with d PTFE, e PVDF, f Parafilm, and g the cyclability comparison, where the PTFE cell failed after 580 cycles. (1 C = 200 mA g−1).",
			"url": "https://media.springernature.com/full/springer-static/image/art%3A10.1038%2Fs41467-025-66082-3/MediaObjects/41467_2025_66082_Fig5_HTML.png",
			"figure_path": "user_test_break/figures/s41467-025-66082-3_fig5.png",
			"article_id": "s41467-025-66082-3",
		}
	]))

	await db.execute(insert(exsclaim.Subfigure).values([
		{
			"run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4",
			"id": "s41467-025-66082-3-fig1-d",
			"classification_code": "GR",
			"classification_confidence": 0.7372440099716187,
			"confidence": 0.9659854769706726,
			"height": 448,
			"width": 697,
			"nm_height": None,
			"nm_width": None,
			"x1": 0,
			"y1": 368,
			"x2": 697,
			"y2": 816,
			"caption": "The comparisons of materials cost",
			"keywords": ["Materials", "Comparison"],
			"figure_id": "s41467-025-66082-3-fig1",
			"caption_input_tokens": None,
			"caption_output_tokens": None
		},
		{
			"run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4",
			"id": "s41467-025-66082-3-fig4-d",
			"classification_code": "GR",
			"classification_confidence": 0.9783459305763245,
			"confidence": 0.9577516913414001,
			"height": 571,
			"width": 797,
			"nm_height": None,
			"nm_width": None,
			"x1": 1,
			"y1": 571,
			"x2": 798,
			"y2": 1142,
			"caption": "The ionic tortuosities",
			"keywords": ["Electrodes", "Materials"],
			"figure_id": "s41467-025-66082-3-fig4",
			"caption_input_tokens": None,
			"caption_output_tokens": None
		},
		{
			"run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4",
			"id": "s41467-025-66082-3-fig4-h",
			"classification_code": "GR",
			"classification_confidence": 0.9238795042037964,
			"confidence": 0.9501396417617798,
			"height": 542,
			"width": 523,
			"nm_height": None,
			"nm_width": None,
			"x1": 1121,
			"y1": 1176,
			"x2": 1644,
			"y2": 1718,
			"caption": "",
			"keywords": [],
			"figure_id": "s41467-025-66082-3-fig4",
			"caption_input_tokens": None,
			"caption_output_tokens": None
		},
		{
			"run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4",
			"id": "s41467-025-66082-3-fig1-e",
			"classification_code": "PT",
			"classification_confidence": 0.8040863275527954,
			"confidence": 0.9644704461097717,
			"height": 442,
			"width": 716,
			"nm_height": None,
			"nm_width": None,
			"x1": 732,
			"y1": 376,
			"x2": 1448,
			"y2": 818,
			"caption": "The comparisons of GWP to identify the economic and environmental impact.",
			"keywords": ["Materials", "Comparison"],
			"figure_id": "s41467-025-66082-3-fig1",
			"caption_input_tokens": None,
			"caption_output_tokens": None
		},
		{
			"run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4",
			"id": "s41467-025-66082-3-fig1-a",
			"classification_code": "GR",
			"classification_confidence": 0.9336679577827454,
			"confidence": 0.9539667367935181,
			"height": 351,
			"width": 490,
			"nm_height": None,
			"nm_width": None,
			"x1": 87,
			"y1": 1,
			"x2": 577,
			"y2": 352,
			"caption": "The binder chemistry comparison represents the molecular structure.",
			"keywords": ["Materials", "Comparison"],
			"figure_id": "s41467-025-66082-3-fig1",
			"caption_input_tokens": None,
			"caption_output_tokens": None
		},
		{
			"run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4",
			"id": "s41467-025-66082-3-fig1-f",
			"classification_code": "IL",
			"classification_confidence": 0.536908745765686,
			"confidence": 0.9226866960525513,
			"height": 664,
			"width": 1278,
			"nm_height": None,
			"nm_width": None,
			"x1": 144,
			"y1": 844,
			"x2": 1422,
			"y2": 1508,
			"caption": "The potential fabrication process schematics on the powder-to-electrode concept involved pressing and pattern-coated electrode formation.",
			"keywords": ["Materials", "Comparison"],
			"figure_id": "s41467-025-66082-3-fig1",
			"caption_input_tokens": None,
			"caption_output_tokens": None
		},
		{
			"run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4",
			"id": "s41467-025-66082-3-fig1-b",
			"classification_code": "GR",
			"classification_confidence": 0.7939702272415161,
			"confidence": 0.8905177712440491,
			"height": 349,
			"width": 483,
			"nm_height": None,
			"nm_width": None,
			"x1": 600,
			"y1": 0,
			"x2": 1083,
			"y2": 349,
			"caption": "The binder chemistry comparison represents the molecular structure.",
			"keywords": ["Materials", "Comparison"],
			"figure_id": "s41467-025-66082-3-fig1",
			"caption_input_tokens": None,
			"caption_output_tokens": None
		},
		{
			"run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4",
			"id": "s41467-025-66082-3-fig2-b",
			"classification_code": "GR",
			"classification_confidence": 0.9880421161651611,
			"confidence": 0.9826743006706238,
			"height": 525,
			"width": 709,
			"nm_height": None,
			"nm_width": None,
			"x1": 0,
			"y1": 610,
			"x2": 709,
			"y2": 1135,
			"caption": "DSC curves featuring Tg of binders",
			"keywords": ["FTIR", "DSC"],
			"figure_id": "s41467-025-66082-3-fig2",
			"caption_input_tokens": None,
			"caption_output_tokens": None
		},
		{
			"run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4",
			"id": "s41467-025-66082-3-fig2-c",
			"classification_code": "GR",
			"classification_confidence": 0.5876326560974121,
			"confidence": 0.9570095539093018,
			"height": 490,
			"width": 699,
			"nm_height": None,
			"nm_width": None,
			"x1": 748,
			"y1": 607,
			"x2": 1447,
			"y2": 1097,
			"caption": "HOMO-LUMO energy gap of polymer segments estimate an electrochemical window",
			"keywords": ["FTIR", "DSC"],
			"figure_id": "s41467-025-66082-3-fig2",
			"caption_input_tokens": None,
			"caption_output_tokens": None
		},
		{
			"run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4",
			"id": "s41467-025-66082-3-fig2-a",
			"classification_code": "GR",
			"classification_confidence": 0.9938086867332458,
			"confidence": 0.9376839995384216,
			"height": 573,
			"width": 1410,
			"nm_height": None,
			"nm_width": None,
			"x1": 24,
			"y1": 0,
			"x2": 1434,
			"y2": 573,
			"caption": "FTIR spectra demonstrating C-F and C-H bond signals",
			"keywords": ["FTIR", "DSC"],
			"figure_id": "s41467-025-66082-3-fig2",
			"caption_input_tokens": None,
			"caption_output_tokens": None
		},
		{
			"run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4",
			"id": "s41467-025-66082-3-fig3-g",
			"classification_code": "DF",
			"classification_confidence": 0.587363600730896,
			"confidence": 0.9744086265563965,
			"height": 392,
			"width": 556,
			"nm_height": 147368.4,
			"nm_width": 209022.5,
			"x1": 598,
			"y1": 1069,
			"x2": 1154,
			"y2": 1461,
			"caption": "PVDF",
			"keywords": ["Materials", "Characterization"],
			"figure_id": "s41467-025-66082-3-fig3",
			"caption_input_tokens": None,
			"caption_output_tokens": None
		},
		{
			"run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4",
			"id": "s41467-025-66082-3-fig3-f",
			"classification_code": "MC",
			"classification_confidence": 0.49990925192832947,
			"confidence": 0.9738821387290955,
			"height": 391,
			"width": 557,
			"nm_height": 148106,
			"nm_width": 210984.8,
			"x1": 3,
			"y1": 1070,
			"x2": 560,
			"y2": 1461,
			"caption": "PTFE",
			"keywords": ["Materials", "Characterization"],
			"figure_id": "s41467-025-66082-3-fig3",
			"caption_input_tokens": None,
			"caption_output_tokens": None
		},
		{
			"run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4",
			"id": "s41467-025-66082-3-fig3-d",
			"classification_code": "MC",
			"classification_confidence": 0.9990542531013489,
			"confidence": 0.9684268236160278,
			"height": 392,
			"width": 555,
			"nm_height": 146268.6,
			"nm_width": 207089.5,
			"x1": 597,
			"y1": 650,
			"x2": 1152,
			"y2": 1042,
			"caption": "Cross-sectional SEM and C atom EDS mapping images of PVDF",
			"keywords": ["Materials", "Characterization"],
			"figure_id": "s41467-025-66082-3-fig3",
			"caption_input_tokens": None,
			"caption_output_tokens": None
		},
		{
			"run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4",
			"id": "s41467-025-66082-3-fig3-h",
			"classification_code": "MC",
			"classification_confidence": 0.5806673765182495,
			"confidence": 0.9675072431564331,
			"height": 393,
			"width": 557,
			"nm_height": 85064.9,
			"nm_width": 120562.7,
			"x1": 1192,
			"y1": 1066,
			"x2": 1749,
			"y2": 1459,
			"caption": "Parafilm-based ones",
			"keywords": ["Materials", "Characterization"],
			"figure_id": "s41467-025-66082-3-fig3",
			"caption_input_tokens": None,
			"caption_output_tokens": None
		},
		{
			"run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4",
			"id": "s41467-025-66082-3-fig3-a",
			"classification_code": "GR",
			"classification_confidence": 0.989629328250885,
			"confidence": 0.9644325375556946,
			"height": 621,
			"width": 854,
			"nm_height": None,
			"nm_width": None,
			"x1": 0,
			"y1": 2,
			"x2": 854,
			"y2": 623,
			"caption": "Depth-dependent cohesion measurement of electrodes",
			"keywords": ["Materials", "Characterization"],
			"figure_id": "s41467-025-66082-3-fig3",
			"caption_input_tokens": None,
			"caption_output_tokens": None
		},
		{
			"run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4",
			"id": "s41467-025-66082-3-fig3-c",
			"classification_code": "MC",
			"classification_confidence": 0.9996415376663208,
			"confidence": 0.9591740369796753,
			"height": 392,
			"width": 559,
			"nm_height": 145185.1,
			"nm_width": 207037,
			"x1": 2,
			"y1": 652,
			"x2": 561,
			"y2": 1044,
			"caption": "Cross-sectional SEM and C atom EDS mapping images of PTFE",
			"keywords": ["Materials", "Characterization"],
			"figure_id": "s41467-025-66082-3-fig3",
			"caption_input_tokens": None,
			"caption_output_tokens": None
		},
		{
			"run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4",
			"id": "s41467-025-66082-3-fig3-b",
			"classification_code": "GR",
			"classification_confidence": 0.8706983923912048,
			"confidence": 0.9574946761131287,
			"height": 579,
			"width": 870,
			"nm_height": None,
			"nm_width": None,
			"x1": 868,
			"y1": 0,
			"x2": 1738,
			"y2": 579,
			"caption": "Adhesion measurement with and without primer coating. The error bars represent the standard deviation (σ) from three independent measurements for each experimental group. The adhesion and cohesion values were determined as the averaged horizontal force measured within the defined loading region.",
			"keywords": ["Materials", "Characterization"],
			"figure_id": "s41467-025-66082-3-fig3",
			"caption_input_tokens": None,
			"caption_output_tokens": None
		},
		{
			"run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4",
			"id": "s41467-025-66082-3-fig3-e",
			"classification_code": "MC",
			"classification_confidence": 0.9996362924575806,
			"confidence": 0.9484037160873413,
			"height": 392,
			"width": 558,
			"nm_height": 85217.3,
			"nm_width": 121304.3,
			"x1": 1191,
			"y1": 650,
			"x2": 1749,
			"y2": 1042,
			"caption": "Cross-sectional SEM and C atom EDS mapping images of Parafilm-based ones",
			"keywords": ["Materials", "Characterization"],
			"figure_id": "s41467-025-66082-3-fig3",
			"caption_input_tokens": None,
			"caption_output_tokens": None
		},
		{
			"run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4",
			"id": "s41467-025-66082-3-fig4-e",
			"classification_code": "GR",
			"classification_confidence": 0.9453848600387573,
			"confidence": 0.9767978191375732,
			"height": 612,
			"width": 809,
			"nm_height": None,
			"nm_width": None,
			"x1": 827,
			"y1": 562,
			"x2": 1636,
			"y2": 1174,
			"caption": "and",
			"keywords": ["Electrodes", "Materials"],
			"figure_id": "s41467-025-66082-3-fig4",
			"caption_input_tokens": None,
			"caption_output_tokens": None
		},
		{
			"run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4",
			"id": "s41467-025-66082-3-fig4-a",
			"classification_code": "GR",
			"classification_confidence": 0.8987736105918884,
			"confidence": 0.9716008901596069,
			"height": 534,
			"width": 526,
			"nm_height": None,
			"nm_width": None,
			"x1": 0,
			"y1": 2,
			"x2": 526,
			"y2": 536,
			"caption": "Nyquist EIS data for a PTFE",
			"keywords": ["Electrodes", "Materials"],
			"figure_id": "s41467-025-66082-3-fig4",
			"caption_input_tokens": None,
			"caption_output_tokens": None
		},
		{
			"run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4",
			"id": "s41467-025-66082-3-fig4-c",
			"classification_code": "GR",
			"classification_confidence": 0.6733617186546326,
			"confidence": 0.970421314239502,
			"height": 532,
			"width": 529,
			"nm_height": None,
			"nm_width": None,
			"x1": 1116,
			"y1": 3,
			"x2": 1645,
			"y2": 535,
			"caption": "and c Parafilm-based electrodes.",
			"keywords": ["Electrodes", "Materials"],
			"figure_id": "s41467-025-66082-3-fig4",
			"caption_input_tokens": None,
			"caption_output_tokens": None
		},
		{
			"run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4",
			"id": "s41467-025-66082-3-fig4-b",
			"classification_code": "GR",
			"classification_confidence": 0.9300417304039001,
			"confidence": 0.9658858180046082,
			"height": 531,
			"width": 534,
			"nm_height": None,
			"nm_width": None,
			"x1": 555,
			"y1": 0,
			"x2": 1089,
			"y2": 531,
			"caption": "PVDF",
			"keywords": ["Electrodes", "Materials"],
			"figure_id": "s41467-025-66082-3-fig4",
			"caption_input_tokens": None,
			"caption_output_tokens": None
		},
		{
			"run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4",
			"id": "s41467-025-66082-3-fig4-f",
			"classification_code": "IL",
			"classification_confidence": 0.46431463956832886,
			"confidence": 0.9317162036895752,
			"height": 541,
			"width": 518,
			"nm_height": None,
			"nm_width": None,
			"x1": 0,
			"y1": 1176,
			"x2": 518,
			"y2": 1717,
			"caption": "h DCIR comparison for those binder-based electrodes to identify the comprehensive resistance.",
			"keywords": ["Electrodes", "Materials"],
			"figure_id": "s41467-025-66082-3-fig4",
			"caption_input_tokens": None,
			"caption_output_tokens": None
		},
		{
			"run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4",
			"id": "s41467-025-66082-3-fig4-g",
			"classification_code": "GR",
			"classification_confidence": 0.9407498240470886,
			"confidence": 0.9184001088142395,
			"height": 537,
			"width": 524,
			"nm_height": None,
			"nm_width": None,
			"x1": 556,
			"y1": 1181,
			"x2": 1080,
			"y2": 1718,
			"caption": "(1 C = 200 mA g−1)",
			"keywords": ["Electrodes", "Materials"],
			"figure_id": "s41467-025-66082-3-fig4",
			"caption_input_tokens": None,
			"caption_output_tokens": None
		},
		{
			"run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4",
			"id": "s41467-025-66082-3-fig5-d",
			"classification_code": "GR",
			"classification_confidence": 0.9923965334892273,
			"confidence": 0.9735905528068542,
			"height": 546,
			"width": 605,
			"nm_height": None,
			"nm_width": None,
			"x1": 0,
			"y1": 541,
			"x2": 605,
			"y2": 1087,
			"caption": "The cycling profile of full cells with PTFE",
			"keywords": ["materials", "batteries"],
			"figure_id": "s41467-025-66082-3-fig5",
			"caption_input_tokens": None,
			"caption_output_tokens": None
		},
		{
			"run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4",
			"id": "s41467-025-66082-3-fig5-c",
			"classification_code": "GR",
			"classification_confidence": 0.968789279460907,
			"confidence": 0.973443329334259,
			"height": 537,
			"width": 610,
			"nm_height": None,
			"nm_width": None,
			"x1": 1286,
			"y1": 3,
			"x2": 1896,
			"y2": 540,
			"caption": "Rate capabilities in half-cell configuration for a Parafilm",
			"keywords": ["materials", "batteries"],
			"figure_id": "s41467-025-66082-3-fig5",
			"caption_input_tokens": None,
			"caption_output_tokens": None
		},
		{
			"run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4",
			"id": "s41467-025-66082-3-fig5-b",
			"classification_code": "GR",
			"classification_confidence": 0.6467410326004028,
			"confidence": 0.9699466824531555,
			"height": 542,
			"width": 605,
			"nm_height": None,
			"nm_width": None,
			"x1": 639,
			"y1": 0,
			"x2": 1244,
			"y2": 542,
			"caption": "Rate capabilities in half-cell configuration for a PVDF",
			"keywords": ["materials", "batteries"],
			"figure_id": "s41467-025-66082-3-fig5",
			"caption_input_tokens": None,
			"caption_output_tokens": None
		},
		{
			"run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4",
			"id": "s41467-025-66082-3-fig5-f",
			"classification_code": "GR",
			"classification_confidence": 0.9988412261009216,
			"confidence": 0.9606152176856995,
			"height": 549,
			"width": 621,
			"nm_height": None,
			"nm_width": None,
			"x1": 1284,
			"y1": 543,
			"x2": 1905,
			"y2": 1092,
			"caption": "The cycling profile of full cells with Parafilm",
			"keywords": ["materials", "batteries"],
			"figure_id": "s41467-025-66082-3-fig5",
			"caption_input_tokens": None,
			"caption_output_tokens": None
		},
		{
			"run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4",
			"id": "s41467-025-66082-3-fig5-a",
			"classification_code": "GR",
			"classification_confidence": 0.9508705139160156,
			"confidence": 0.9602010250091553,
			"height": 539,
			"width": 598,
			"nm_height": None,
			"nm_width": None,
			"x1": 0,
			"y1": 3,
			"x2": 598,
			"y2": 542,
			"caption": "Rate capabilities in half-cell configuration for a PTFE",
			"keywords": ["materials", "batteries"],
			"figure_id": "s41467-025-66082-3-fig5",
			"caption_input_tokens": None,
			"caption_output_tokens": None
		},
		{
			"run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4",
			"id": "s41467-025-66082-3-fig5-e",
			"classification_code": "GR",
			"classification_confidence": 0.8192461729049683,
			"confidence": 0.9571378827095032,
			"height": 544,
			"width": 612,
			"nm_height": None,
			"nm_width": None,
			"x1": 641,
			"y1": 548,
			"x2": 1253,
			"y2": 1092,
			"caption": "The cycling profile of full cells with PVDF",
			"keywords": ["materials", "batteries"],
			"figure_id": "s41467-025-66082-3-fig5",
			"caption_input_tokens": None,
			"caption_output_tokens": None
		},
		{
			"run_id": "019ba4c7-b23f-7e32-b072-a104b88183d4",
			"id": "s41467-025-66082-3-fig5-g",
			"classification_code": "GR",
			"classification_confidence": 0.7368174195289612,
			"confidence": 0.7501764297485352,
			"height": 670,
			"width": 1811,
			"nm_height": None,
			"nm_width": None,
			"x1": 0,
			"y1": 1108,
			"x2": 1811,
			"y2": 1778,
			"caption": "The cyclability comparison, where the PTFE cell failed after 580 cycles",
			"keywords": ["materials", "batteries"],
			"figure_id": "s41467-025-66082-3-fig5",
			"caption_input_tokens": None,
			"caption_output_tokens": None
		}
	]))


@pytest.mark.asyncio
async def test_orm(db: AsyncSession):
	# Insert test data

	async with db:
		results = await db.execute(select(exsclaim.Article))
		articles = results.scalars().fetchall()

		if len(articles) == 0:
			await upload_test_data(db)
			results = await db.execute(select(exsclaim.Article))
			articles = results.scalars().fetchall()

		assert len(articles) > 0, "There are no articles in the database to test"

		article = articles[0]
		assert isinstance(article, exsclaim.Article), f"The first returned value was not an exsclaim.Article, instead it was {type(article).__name__}"

		authors = article.authors
		assert len(authors) > 0, f"There are no authors for article {article.id} to test."
		author = authors[0]
		assert isinstance(author, exsclaim.Author), f"The first author was was not an exsclaim.Author, instead it was {type(author).__name__}."

		# Just making sure this doesn't crash
		await author.articles

		figures = await article.figures
		figure = figures[0]
		assert isinstance(figure, exsclaim.Figure), f"The first figure was not an exsclaim.Figure, instead it was {type(figure).__name__}."

		subfigures = await figure.subfigures
		subfigure = subfigures[0]
		assert isinstance(subfigure, exsclaim.Subfigure), f"The first subfigure was not an exsclaim.Subfigure, instead it was {type(subfigure).__name__}."

		runs = await article.runs
		run = runs[0]
		assert isinstance(run, exsclaim.Run), f"The first run was not an exsclaim.Results, instead it was {type(run).__name__}."

		user = run.owner
		assert isinstance(user, exsclaim.User), f"The owner was not an exsclaim.User, instead it was {type(run).__name__}: {run!r}."

		user_runs = await user.runs
		assert len(user_runs) > 0, f"There are no runs for user {user.id} to test, even though this user was found from a run."


async def main():
	async with exsclaim.get_db_session() as db:
		await test_orm(db)


if __name__ == "__main__":
	import asyncio
	asyncio.run(main())
